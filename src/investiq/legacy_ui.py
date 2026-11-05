"""Explicit entry point for the optional, former Streamlit interface."""

from pathlib import Path
import sys


def main(argv: list[str] | None = None) -> int:
    try:
        from streamlit.web import cli
    except ModuleNotFoundError as error:
        if error.name != "streamlit" and not (error.name or "").startswith("streamlit."):
            raise
        print("Para abrir la web principal, ejecuta bash run_web.sh o investiq-app.", file=sys.stderr)
        print("La interfaz anterior necesita el extra: python -m pip install -e '.[legacy-ui]'", file=sys.stderr)
        return 1

    arguments = list(sys.argv[1:] if argv is None else argv)
    previous_argv = sys.argv
    try:
        sys.argv = ["streamlit", "run", str(Path(__file__).with_name("app.py")), *arguments]
        return cli.main()
    finally:
        sys.argv = previous_argv


if __name__ == "__main__":
    raise SystemExit(main())
