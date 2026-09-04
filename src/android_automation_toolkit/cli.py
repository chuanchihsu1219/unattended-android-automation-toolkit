from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo import build_demo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reliability-first unattended Android automation toolkit"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="run the deterministic synthetic pipeline")
    demo.add_argument("--output", type=Path, default=Path("runtime/demo"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        result = build_demo(args.output.resolve())
        print(json.dumps(result, indent=2))
        return 0
    return 2
