"""PyInstaller entry point for bCNC.

Three issues must be handled when frozen by PyInstaller:

1. Runtime imports. ``bCNC/__main__.py`` computes its own ``PRGPATH`` from
   ``__file__`` and appends ``lib/``, ``plugins/``, ``controllers/`` to
   ``sys.path``. That works for the lib (a real package) but plugins/ and
   controllers/ are plain directories of .py loaded by name via
   ``glob.glob + __import__`` in ``ToolsPage.py``/``Sender.py``. We must put
   those directories on ``sys.path`` ourselves.

2. gettext ``_``. Many modules use ``_()`` at class-definition time
   (e.g. ``bFileDialog.OpenDialog._title = _("Open")``). ``_`` is installed
   into builtins by ``Helpers`` via ``gettext.install()``. The normal
   ``__main__.main()`` imports ``Helpers`` first; we must do the same BEFORE
   importing anything that transitively touches ``_`` (Utils -> Ribbon ->
   tkExtra -> bFileDialog).

3. Data-file root. ``Utils``/``Helpers`` set ``prgpath`` at import time using
   ``sys.argv[0]`` (the exe location). For onedir that happens to match the
   data dir; for ONEFILE the data is extracted to the ``sys._MEIPASS`` temp
   dir, so globs for plugins/controllers/icons and the bundled ``bCNC.ini``
   would resolve to the wrong place. We patch ``prgpath``/``iniSystem`` to
   ``sys._MEIPASS`` after import, before ``main()`` runs.

``sys._MEIPASS`` is set by PyInstaller for both onedir and onefile and points
at the directory holding the bundled data files, so it is the correct root in
either mode.
"""

import os
import sys
import traceback


def _frozen_data_root():
    if not getattr(sys, "frozen", False):
        return None
    return getattr(sys, "_MEIPASS", None) or os.path.dirname(
        os.path.abspath(sys.executable)
    )


# With console=False (windowed build) PyInstaller sets sys.stdout/stderr to
# None. bCNC (and tkinter) call print()/sys.stdout.write() in many places,
# which would raise AttributeError. Replace None with a real sink BEFORE any
# bCNC code runs. Route to bCNC.console.log next to the exe so output is
# still diagnosable; fall back to devnull if the file is unwritable.
def _fix_stdio():
    if sys.stdout is None or sys.stderr is None:
        sink = None
        try:
            log = os.path.join(
                os.path.dirname(os.path.abspath(sys.executable)),
                "bCNC.console.log",
            )
            sink = open(log, "w", encoding="utf-8", buffering=1)
        except Exception:
            sink = open(os.devnull, "w", encoding="utf-8")
        if sys.stdout is None:
            sys.stdout = sink
        if sys.stderr is None:
            sys.stderr = sink


_fix_stdio()


_root = _frozen_data_root()

# (1) Make runtime-imported packages discoverable.
if _root:
    for sub in ("plugins", "controllers", "lib"):
        candidate = os.path.join(_root, sub)
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.insert(0, candidate)

# Importing bCNC.__main__ runs its top-level (sys.path setup, defines main()).
# It does not touch _(), so it is safe before Helpers.
from bCNC.__main__ import main  # noqa: E402

# (2) Install gettext _() into builtins BEFORE any import that uses it.
# Helpers.py calls gettext.install(...). Must precede Utils (-> Ribbon ->
# tkExtra -> bFileDialog, which uses _() at class-definition time).
import Helpers  # noqa: E402, F401

# (3) Repoint data-root-dependent attributes that were frozen at import time
# using sys.argv[0] (the exe location) rather than the bundle data dir.
if _root:
    import Utils  # noqa: E402

    Utils.prgpath = _root
    Utils.iniSystem = os.path.join(_root, f"{Utils.__prg__}.ini")
    Helpers.prgpath = _root


def _write_crash_log(exc):
    # console=False hides stderr; write the traceback next to the exe so the
    # user (and CI) can see why a windowed launch died.
    try:
        log = os.path.join(os.path.dirname(os.path.abspath(sys.executable)),
                           "bCNC.crash.log")
        with open(log, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _write_crash_log(sys.exc_info()[1])
        raise
