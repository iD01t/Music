import sys
import argparse

try:
    from .gui import gui_main, tk_available
except ImportError:
    tk_available = False

    def gui_main():
        print("GUI cannot be started due to import errors.", file=sys.stderr)
        return 1


from .cli import cli_main
from .helpers import ensure_eula_accepted


def main() -> int:
    """
    Main entry point for the application.
    Decides whether to run the GUI or CLI.
    """
    # Lightweight EULA check
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--accept-eula", action="store_true")
    known_args, other_args = parser.parse_known_args()
    if not ensure_eula_accepted(cli_accept=known_args.accept_eula):
        # In GUI mode, a dialog will be shown. In CLI, this is a failure.
        if not tk_available or "--gui" not in sys.argv[1:]:
            print("EULA not accepted. Exiting.", file=sys.stderr)
            return 1

    # Decide on GUI vs CLI
    if "--gui" in sys.argv[1:] or (tk_available and len(sys.argv) == 1):
        return gui_main()
    else:
        return cli_main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
