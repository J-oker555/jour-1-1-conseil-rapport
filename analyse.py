from __future__ import annotations

import argparse
from pathlib import Path

from src.bat.reporting import append_run_header


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyse des phases 7 a 12 sans fuite de donnees."
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/raw/ufo.csv"),
        help="Chemin vers le fichier de transmission CSV.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("RAPPORT.md"),
        help="Chemin du rapport Markdown a mettre a jour.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verifie la configuration sans lancer l'analyse complete.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.dry_run:
        print(f"data={args.data}")
        print(f"report={args.report}")
        return 0

    if not args.data.exists():
        raise FileNotFoundError(
            f"Donnees introuvables: {args.data}. "
            "Place le CSV dans data/raw/ ou passe --data."
        )

    append_run_header(args.report)
    raise NotImplementedError(
        "Architecture initialisee. Implementer les phases 7 a 12 dans src/bat/."
    )


if __name__ == "__main__":
    raise SystemExit(main())

