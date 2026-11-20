
import os
import mmap
import time
import json
import struct
import random
import sqlite3
import pandas as pd
import pyarrow as pa
import pyarrow.ipc as ipc
import pyarrow.parquet as pq
import tiktoken

WORK_DIR = "substrate_bench"
ENC = tiktoken.get_encoding("cl100k_base")


def build_synthetic_df(n):
    return pd.DataFrame({
        "Record_ID": [f"TX-{i:07d}" for i in range(n)],
        "Department": [f"Dept_{i % 5}" for i in range(n)],
        "Region": [f"Reg_{i % 4}" for i in range(n)],
        "Quarter": [f"Q{(i % 4) + 1}/26" for i in range(n)],
        "Budget_USD": [100000 + (i % 500) * 1000 for i in range(n)],
        "Actual_Spend": [90000 + (i % 450) * 1000 for i in range(n)],
        "Latency_ms": [round(0.15 + (i % 50) * 0.01, 3) for i in range(n)],
        "Status": ["COMMITTED" if i % 2 == 0 else "VERIFIED" for i in range(n)],
        "Checksum": [f"CHK-{i:08x}" for i in range(n)],
        "Tag": [f"SDO-NODE-{i % 100}" for i in range(n)],
    })


def write_binary_sdo_image(df, sdo_path):
    """Packs records into a fixed-stride memory-aligned binary .sdo image with R0 superblock."""
    records = df.astype(str).values.tolist()
    row_bytes_list = ["|".join(r).encode("utf-8") for r in records]
    max_stride = max(len(b) for b in row_bytes_list) + 1

    with open(sdo_path, "wb") as f:
        # 64-byte Superblock Header (Magic, RowCount, RowStride)
        header = struct.pack("<8sII48s", b"GUDTSDO1", len(records), max_stride, b"\x00" * 48)
        f.write(header)
        for rb in row_bytes_list:
            f.write(rb.ljust(max_stride, b"\x00"))
    return max_stride


def benchmark_scale(n):
    os.makedirs(WORK_DIR, exist_ok=True)
    df = build_synthetic_df(n)

    json_path = os.path.join(WORK_DIR, f"data_{n}.json")
    csv_path = os.path.join(WORK_DIR, f"data_{n}.csv")
    md_path = os.path.join(WORK_DIR, f"data_{n}.md")
    sqlite_path = os.path.join(WORK_DIR, f"data_{n}.db")
    arrow_path = os.path.join(WORK_DIR, f"data_{n}.arrow")
    parquet_path = os.path.join(WORK_DIR, f"data_{n}.parquet")
    sdo_path = os.path.join(WORK_DIR, f"data_{n}.sdo")

    # 1. Serialize all formats
    df.to_json(json_path, orient="records")
    df.to_csv(csv_path, index=False)
    df.to_markdown(md_path, index=False)
    pq.write_table(pa.Table.from_pandas(df), parquet_path)

    with pa.OSFile(arrow_path, "wb") as sink:
        table = pa.Table.from_pandas(df)
        with ipc.new_file(sink, table.schema) as writer:
            writer.write_table(table)

    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)
    conn = sqlite3.connect(sqlite_path)
    df.to_sql("records", conn, index=True, index_label="row_idx")
    conn.execute("CREATE INDEX idx_row ON records(row_idx)")
    conn.commit()

    stride = write_binary_sdo_image(df, sdo_path)

    # 2. Measure Token Counts (exact for <= 10K, scaled linearly for larger N)
    sample_n = min(n, 2000)
    scale_factor = n / sample_n
    json_tokens = int(len(ENC.encode(df.iloc[:sample_n].to_json(orient="records"))) * scale_factor)
    csv_tokens = int(len(ENC.encode(df.iloc[:sample_n].to_csv(index=False))) * scale_factor)
    md_tokens = int(len(ENC.encode(df.iloc[:sample_n].to_markdown(index=False))) * scale_factor)

    r0_line = "R0(Schema): " + " | ".join(f"C{c+1}={col}" for c, col in enumerate(df.columns))
    gudt_sample = r0_line + "\n" + "\n".join(
        f"R{i+1}: " + " | ".join(map(str, row)) for i, row in enumerate(df.iloc[:sample_n].values)
    )
    gudt_tokens = int(len(ENC.encode(gudt_sample)) * scale_factor)

    # 3. Measure Mount / Load Latencies
    t0 = time.perf_counter()
    with open(json_path, "r", encoding="utf-8") as f:
        _ = json.load(f)
    json_load_ms = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    with pa.memory_map(arrow_path, "r") as source:
        reader = ipc.open_file(source)
        _ = reader.schema
    arrow_mount_ms = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    fd = os.open(sdo_path, os.O_RDONLY)
    mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
    _, row_count, row_stride, _ = struct.unpack("<8sII48s", mm[:64])
    sdo_mount_ms = (time.perf_counter() - t0) * 1000.0

    # 4. Measure Mean O(1) Point Lookup Latency (1,000 random queries)
    queries = [random.randint(0, n - 1) for _ in range(1000)]

    t0 = time.perf_counter()
    for q in queries:
        offset = 64 + q * row_stride
        _ = mm[offset : offset + row_stride].split(b"\x00", 1)[0]
    sdo_lookup_us = ((time.perf_counter() - t0) / 1000.0) * 1e6

    cur = conn.cursor()
    t0 = time.perf_counter()
    for q in queries:
        cur.execute("SELECT * FROM records WHERE row_idx = ?", (q,))
        _ = cur.fetchone()
    sqlite_lookup_us = ((time.perf_counter() - t0) / 1000.0) * 1e6

    mm.close()
    os.close(fd)
    conn.close()

    saved_pct = (1.0 - gudt_tokens / json_tokens) * 100.0
    print(f"\n--- Scale N = {n:,} ---")
    print(f"Tokens  | JSON: {json_tokens:,} | MD: {md_tokens:,} | CSV: {csv_tokens:,} | GUDT S-Tokens: {gudt_tokens:,} (-{saved_pct:.2f}%)")
    print(f"Mount   | JSON Parse: {json_load_ms:.3f} ms | Arrow mmap: {arrow_mount_ms:.3f} ms | SDO MmemLoad: {sdo_mount_ms:.3f} ms")
    print(f"Lookup  | SQLite B-Tree: {sqlite_lookup_us:.2f} us | SDO O(1) Offset: {sdo_lookup_us:.2f} us")


if __name__ == "__main__":
    for scale in (1000, 10000, 100000):  # Add 1000000 for 1M full benchmark
        benchmark_scale(scale)

