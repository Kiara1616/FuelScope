"""Importa un CSV local adquirido por un canal autorizado."""

import argparse
import json
from pathlib import Path

from fuelscope.snapshot import publish_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    status, manifest = publish_snapshot(
        args.csv,
        args.output,
        contract["mapping"],
        contract["units"],
        contract["source_url"],
        contract["license"],
    )
    print(json.dumps({"status": status, "source_sha256": manifest["source_sha256"]}))


if __name__ == "__main__":
    main()
