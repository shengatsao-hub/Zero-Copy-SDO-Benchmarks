
import os
import json
import random
from openai import OpenAI

# Configure via environment variables before running:
# export LLM_API_KEY="your_api_key"
# export LLM_BASE_URL="https://api.deepseek.com"
# export LLM_MODEL="deepseek-chat"
API_KEY = os.getenv("LLM_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("LLM_MODEL", "deepseek-chat")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


def build_tableqa_dataset(num_questions=100):
    random.seed(42)
    departments = ["Cloud_Infra", "AI_Kernel", "Data_Fabric", "Security_Ops", "FinTech_Core"]
    regions = ["AP-Taipei", "NA-East", "EU-Central", "AP-Tokyo"]
    statuses = ["COMMITTED", "PENDING", "VERIFIED", "AUDITED"]

    dataset = []
    for q_idx in range(num_questions):
        headers = [
            "Record_ID", "Department", "Region", "Quarter",
            "Budget_USD", "Actual_Spend_USD", "Latency_ms", "Status"
        ]
        rows = []
        target_row_idx = random.randint(5, 24)

        for r_idx in range(30):
            rec_id = f"TX-{1000 + q_idx * 30 + r_idx}"
            dept = departments[(r_idx + q_idx) % 5]
            reg = regions[(r_idx * 3 + q_idx) % 4]
            qtr = f"Q{(r_idx % 4) + 1}/26"
            budget = random.randint(50, 500) * 1000
            spend = budget - random.randint(-20, 80) * 500
            lat = round(0.12 + (r_idx * 0.03) + (q_idx % 7) * 0.01, 3)
            stat = statuses[(r_idx + q_idx) % 4]
            rows.append([rec_id, dept, reg, qtr, str(budget), str(spend), str(lat), stat])

        target = rows[target_row_idx]
        if q_idx % 2 == 0:
            question = f"What is the exact Latency_ms for Record_ID {target[0]} in Region {target[2]}?"
            answer = target[6]
        else:
            diff = int(target[4]) - int(target[5])
            question = f"For Record_ID {target[0]} ({target[1]}), calculate Budget_USD minus Actual_Spend_USD."
            answer = str(diff)

        dataset.append({
            "headers": headers,
            "rows": rows,
            "question": question,
            "answer": answer
        })
    return dataset


def run_benchmark():
    ds = build_tableqa_dataset(100)
    results = {
        "JSON": {"correct": 0, "tokens": 0},
        "CSV": {"correct": 0, "tokens": 0},
        "GUDT_SToken": {"correct": 0, "tokens": 0}
    }

    print(f"Running N=100 Table-QA Reasoning & Token Benchmark on {MODEL_NAME}...")

    for idx, item in enumerate(ds):
        headers = item["headers"]
        rows = item["rows"]
        question = item["question"]
        gold = item["answer"].strip().lower()

        json_str = json.dumps([dict(zip(headers, r)) for r in rows], ensure_ascii=False)
        csv_str = "\n".join([",".join(headers)] + [",".join(r) for r in rows])
        r0 = "R0(Schema): " + " | ".join(f"C{c+1}={h}" for c, h in enumerate(headers))
        body = "\n".join(f"R{r+1}: " + " | ".join(row) for r, row in enumerate(rows))
        gudt_str = f"{r0}\n{body}"

        prompts = {
            "JSON": f"Table (JSON):\n{json_str}\n\nQuestion: {question}\nOutput ONLY the exact final number/value without any explanation:",
            "CSV": f"Table (CSV):\n{csv_str}\n\nQuestion: {question}\nOutput ONLY the exact final number/value without any explanation:",
            "GUDT_SToken": f"SDO Coordinate Matrix:\n{gudt_str}\n\nQuestion: {question}\nOutput ONLY the exact final number/value without any explanation:"
        }

        for fmt, prompt in prompts.items():
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=32
            )
            if resp.usage and resp.usage.prompt_tokens:
                results[fmt]["tokens"] += resp.usage.prompt_tokens

            pred = (resp.choices[0].message.content or "").strip().lower().replace(",", "")
            if gold in pred:
                results[fmt]["correct"] += 1

        if (idx + 1) % 20 == 0:
            print(f"Completed {idx + 1}/100 evaluations...")

    print("\n==================== FINAL LLM TABLE-QA RESULTS (N=100) ====================")
    json_tokens = results["JSON"]["tokens"]
    for fmt, res in results.items():
        acc = res["correct"]
        tok = res["tokens"]
        saved = (1.0 - tok / json_tokens) * 100.0 if (fmt != "JSON" and json_tokens > 0) else 0.0
        print(f"{fmt:12s} | Accuracy: {acc:5.1f}% | Native Prompt Tokens: {tok:9,d} | Savings vs JSON: {saved:5.2f}%")


if __name__ == "__main__":
    run_benchmark()

