#!/usr/bin/env python3
"""Run the small Anthropic backend probe for DriftGuard.

This script is designed for local shells or Google Colab. It runs:

1. scripted_local baseline on the bundled pilot probe manifest
2. anthropic_messages backend on the same slice
3. result summarization
4. paired backend comparison
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _run(command: list[str], cwd: Path) -> None:
    print(f"$ {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=str(cwd), check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the DriftGuard Anthropic probe")
    parser.add_argument("--output-root", default="results/anthropic_probe", help="Output directory for probe artifacts.")
    parser.add_argument("--seed", type=int, default=31, help="Seed to use for both scripted and Anthropic runs.")
    parser.add_argument(
        "--skip-scripted-baseline",
        action="store_true",
        help="Skip the scripted_local comparison run if it already exists.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    output_root = Path(args.output_root)
    summary_root = output_root / "summary_artifacts"

    if "ANTHROPIC_API_KEY" not in os.environ and "DRIFTGUARD_ANTHROPIC_API_KEY" not in os.environ:
        raise SystemExit("ANTHROPIC_API_KEY or DRIFTGUARD_ANTHROPIC_API_KEY must be set before running this probe.")

    if not args.skip_scripted_baseline:
        _run(
            [
                sys.executable,
                "-m",
                "driftguard",
                "run-manifest",
                "pilot_live_backend_probe",
                "--output-root",
                str(output_root),
                "--agent-backend",
                "scripted_local",
                "--seed",
                str(args.seed),
            ],
            repo_root,
        )

    _run(
        [
            sys.executable,
            "-m",
            "driftguard",
            "run-manifest",
            "pilot_live_backend_probe",
            "--output-root",
            str(output_root),
            "--agent-backend",
            "anthropic_messages",
            "--seed",
            str(args.seed),
        ],
        repo_root,
    )
    _run(
        [
            sys.executable,
            "-m",
            "driftguard",
            "summarize-results",
            str(output_root),
            "--output-root",
            str(summary_root),
        ],
        repo_root,
    )
    _run(
        [
            sys.executable,
            "-m",
            "driftguard",
            "compare-agent-backends",
            "--summary-root",
            str(summary_root),
            "--primary-backend",
            "anthropic_messages",
            "--baseline-backend",
            "scripted_local",
            "--context",
            "raw_transcript",
            "--context",
            "ledger_only",
            "--detector",
            "rule_based",
            "--policy",
            "none",
        ],
        repo_root,
    )

    summary_path = summary_root / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    print("")
    print("Anthropic probe complete.")
    print(f"Summary root: {summary_root}")
    print(f"Total backend tokens: {summary.get('total_backend_tokens', 0)}")
    print(f"Total backend requests: {summary.get('total_backend_requests', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
