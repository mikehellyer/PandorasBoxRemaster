"""Entry point for the frozen app (PyInstaller needs a plain script, not a package module)."""
import sys

from pbremaster.ui.app import main

if __name__ == "__main__":
    sys.exit(main())
