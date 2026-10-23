"""Windowed executable entry; the runtime hook installs the guard first."""

from dusty.__main__ import main

raise SystemExit(main())
