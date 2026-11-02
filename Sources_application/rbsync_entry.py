"""Pinned bundled rbsync CLI, using the private application runtime."""
from rbsync.cli import main
if __name__ == '__main__':
    raise SystemExit(main())
