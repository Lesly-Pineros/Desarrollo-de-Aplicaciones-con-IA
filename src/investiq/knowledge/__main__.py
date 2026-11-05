"""Inspect and validate the local knowledge library without an LLM or network."""

import argparse
import json

from investiq.knowledge import KnowledgeValidationError, get_library


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Biblioteca educativa local de InvestiQ")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Validar todos los documentos y sus fuentes")
    commands.add_parser("stats", help="Mostrar cobertura por categoría")
    search = commands.add_parser("search", help="Recuperar pasajes sin llamar al modelo")
    search.add_argument("query")
    search.add_argument("--topic")
    search.add_argument("--limit", type=int, choices=range(1, 9), default=4)
    args = parser.parse_args(argv)
    try:
        library = get_library()
    except KnowledgeValidationError as error:
        print(json.dumps({"status": "invalid", "error": str(error)}, ensure_ascii=False))
        return 1
    if args.command in {"validate", "stats"}:
        report = library.stats()
        if args.command == "validate":
            report = {"status": "valid", **report}
    else:
        report = {"passages": [passage.model_dump(mode="json") for passage in
                               library.search(args.query, topic=args.topic, limit=args.limit)]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
