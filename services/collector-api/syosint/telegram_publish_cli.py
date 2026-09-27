"""Manual second step from gitignored pending artifact to tracked public wire."""
import argparse
from pathlib import Path

from .telegram_export import PublicSchemaError, stage_telegram_wire

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "data/public/telegram-wire.v1.json"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Stage only explicitly reviewed public Telegram leads")
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--pending", type=Path, required=True)
    stage.add_argument("--output", type=Path, default=TARGET)
    stage.add_argument("--confirm-publication", action="store_true", required=True)
    args = parser.parse_args(argv)
    if not args.confirm_publication or args.output.resolve() != TARGET.resolve():
        print("publication-not-confirmed")
        return 2
    try:
        stage_telegram_wire(args.pending, TARGET, TARGET)
    except (PublicSchemaError, OSError):
        print("publication-staging-failed")
        return 1
    print("publication-staged-for-manual-review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
