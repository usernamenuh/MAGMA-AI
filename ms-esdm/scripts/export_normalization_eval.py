"""Export real user queries that change after normalization for manual review."""

import argparse
import csv
from db.session import SessionLocal
from models.chat_histories import ChatHistory
from utils.query_normalizer import normalize_indonesian_query


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="normalization_eval.csv")
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    with SessionLocal() as db, open(args.output, "w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=["original_query", "normalized_query", "replacements", "approved"],
        )
        writer.writeheader()
        rows = (
            db.query(ChatHistory)
            .filter(ChatHistory.role == "user")
            .order_by(ChatHistory.created_at.desc())
            .limit(args.limit)
            .all()
        )
        for row in rows:
            result = normalize_indonesian_query(row.message)
            if not result.changed:
                continue
            writer.writerow({
                "original_query": result.original,
                "normalized_query": result.normalized,
                "replacements": "; ".join(f"{a} -> {b}" for a, b in result.replacements),
                "approved": "",
            })


if __name__ == "__main__":
    main()
