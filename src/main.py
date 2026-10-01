import sys

from .db import init_db
from .discovery import discover
from .research import research_pending
from .analyze import analyze


def main():
    init_db()

    command = sys.argv[1] if len(sys.argv) > 1 else "help"

    if command == "discover":
        discover()

    elif command == "research":
        research_pending()

    elif command == "analyze":
        analyze()

    elif command == "all":
        discover()
        research_pending()
        analyze()

    else:
        print("""
PFE Outreach Agent

Commands:

  python -m src.main discover
  python -m src.main research
  python -m src.main analyze
  python -m src.main all
        """)


if __name__ == "__main__":
    main()