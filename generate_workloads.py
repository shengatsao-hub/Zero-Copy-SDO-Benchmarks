
import os
import json
import random

OUTPUT_DIR = "benchmark_data"


def generate_word_processing_corpus(num_paragraphs=1000):
    """Generates the 1,000-paragraph (~455 KB / ~100-137 page) document corpus."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"wp_100pages_{num_paragraphs}paras.txt")

    sample_sentences = [
        "Enterprise AI infrastructure faces severe latency penalties when decompressing nested XML containers.",
        "By mapping invariant spatial coordinates (Si, Rj, Ck) directly into virtual memory, VMP eliminates heap allocation overhead.",
        "Traditional parsers reconstruct volatile pointer trees across millions of elements prior to semantic inference.",
        "Sovereign Data Objects preserve byte-for-byte parity between non-volatile storage and runtime memory address spaces.",
        "Decoupled R0 schema vectors prevent repetitive key serialization across high-density relational and financial records."
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        for p_idx in range(1, num_paragraphs + 1):
            body = " ".join(sample_sentences[(p_idx + k) % len(sample_sentences)] for k in range(5))
            f.write(f"[Paragraph {p_idx:04d}] {body}\n\n")

    size_kb = os.path.getsize(filepath) / 1024.0
    print(f"Generated {filepath} ({size_kb:.2f} KB, {num_paragraphs} paragraphs)")


def generate_relational_workloads(scales=(1000, 10000, 100000, 1000000)):
    """Generates relational records in JSON, GUDT R0-decoupled stream, and ground-truth text."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    random.seed(42)

    headers = [
        "Record_ID", "Department", "Region", "Quarter", "Budget_USD",
        "Actual_Spend_USD", "Latency_ms", "Status", "Audit_Hash", "Notes"
    ]
    departments = ["Cloud_Infra", "AI_Kernel", "Data_Fabric", "Security_Ops", "FinTech_Core"]
    regions = ["AP-Taipei", "NA-East", "EU-Central", "AP-Tokyo"]
    statuses = ["COMMITTED", "VERIFIED", "AUDITED", "STAGED"]

    for n in scales:
        json_path = os.path.join(OUTPUT_DIR, f"records_{n}.json")
        gudt_path = os.path.join(OUTPUT_DIR, f"records_{n}.gudt.txt")
        gt_path = os.path.join(OUTPUT_DIR, f"data_ground_truth_{n}.txt")

        records = []
        with open(gudt_path, "w", encoding="utf-8") as fg, open(gt_path, "w", encoding="utf-8") as fgt:
            fg.write("R0(Schema): " + " | ".join(f"C{c+1}={h}" for c, h in enumerate(headers)) + "\n")

            for i in range(1, n + 1):
                row = [
                    f"TX-{i:07d}",
                    departments[i % 5],
                    regions[(i * 3) % 4],
                    f"Q{(i % 4) + 1}/26",
                    str((50 + (i % 450)) * 1000),
                    str((40 + (i % 400)) * 1000),
                    f"{0.12 + (i % 100) * 0.003:.3f}",
                    statuses[i % 4],
                    f"SHA256-{i:08x}",
                    "Memory Pipeline Coordinate ZeroCopy Technology Execution Global Substrate"
                ]
                records.append(dict(zip(headers, row)))
                fg.write(f"R{i}: " + " | ".join(row) + "\n")
                fgt.write(f"{i:06d}," + ",".join(f"[C{c+1}] {val}" for c, val in enumerate(row)) + "\n")

        with open(json_path, "w", encoding="utf-8") as fj:
            json.dump(records, fj, separators=(",", ":"))

        print(f"Generated scale N={n:,} -> JSON ({os.path.getsize(json_path)/1024:.1f} KB), GUDT ({os.path.getsize(gudt_path)/1024:.1f} KB)")


if __name__ == "__main__":
    generate_word_processing_corpus(1000)
    generate_relational_workloads((1000, 10000, 100000))  # Add 1000000 for full 1M stress run
