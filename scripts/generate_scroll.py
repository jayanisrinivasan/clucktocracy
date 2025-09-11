# scripts/generate_scroll.py

"""
Generate a whimsical "coop constitution scroll" or episode summary.
Takes data/log.csv and data/memory_snapshots.json and prints a scroll-like output.
"""

import os
import csv
import json
from textwrap import indent


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
LOG_PATH = os.path.join(DATA_DIR, "log.csv")
MEMORY_PATH = os.path.join(DATA_DIR, "memory_snapshots.json")


def generate_scroll():
    scroll_lines = []
    scroll_lines.append("=== 🪶 The Coop Scroll of Clucktocracy 🪶 ===\n")

    # Load log
    if os.path.exists(LOG_PATH):
        scroll_lines.append(">> Chronicles of Actions:\n")
        with open(LOG_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                line = f"[Tick {row['tick']}] {row['agent']} -> {row['action']} ({row['result']})"
                if row["message"]:
                    line += f' "{row["message"]}"'
                scroll_lines.append(indent(line, "  "))
        scroll_lines.append("")

    # Load memory snapshots
    if os.path.exists(MEMORY_PATH):
        scroll_lines.append(">> Memories of the Flock:\n")
        with open(MEMORY_PATH, encoding="utf-8") as f:
            memories = json.load(f)
        for agent, mems in memories.items():
            scroll_lines.append(f"{agent}:")
            for m in mems[-3:]:  # last 3 memories
                scroll_lines.append(indent(f"- {m.get('event','')}", "  "))
        scroll_lines.append("")

    return "\n".join(scroll_lines)


if __name__ == "__main__":
    scroll = generate_scroll()
    print(scroll)

