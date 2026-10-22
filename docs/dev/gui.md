# Qt desktop interface (M3)

The UI uses pinned PySide6 6.9.2 / Qt 6.9.2. The main entry point installs the
network audit hook before GUI imports. Widgets only collect choices and render
state; the M2 coordinator, catalog rules, scanner, exporters and storage remain
the processing implementation.

## Thread boundary

`PrepareWorker`, `ScanWorker`, `BatchWorker` and `SelfTestWorker` run outside
the GUI thread. Signals carry prepared state or copied Job snapshots. Job
updates are handled by a Qt slot on the window. Native stdout/stderr never
enter a widget or log. A collision request waits on a threading event in the
worker while the GUI dialog runs its event loop. The resulting explicit policy
goes back through the coordinator's normal output planner. Apply-to-all is
remembered only for that batch. Closing mid-batch cancels asynchronously,
preserves queue state, then closes after the worker has cleaned up.

The queue stores additive optional numeric duration/elapsed fields under schema
1; older queues still load. Folder metadata probes and model hashing run in
workers. The Vulkan probe can use a selected installed model when Tiny is not
installed. Device re-probing preserves unsaved user choices and does not repeat
first-run or resume dialogs.

Resuming a batch whose original model is no longer installed requires an
explicit choice of an installed replacement before Start is enabled. Startup
also removes the known probe/self-test work areas, so interruption during
graphics preparation cannot leave an old WAV that prevents the next probe.

Qt's [QThread documentation](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)
describes the worker thread and queued signal boundary. APIs were checked with
the installed 6.9.2 bindings, including style hints, model/view data changes,
QStyleOptionProgressBar properties and QFileDialog behavior. The online 6.9
documentation redirects to the current documentation. Some public style-option
properties are missing from the installed type stubs; the narrow dynamic
annotation in the delegate is exercised by real offscreen paints.

## Copy, language list and appearance

`app/messages.py` is the single UI copy catalog, including the approved privacy
and accuracy wording and every failure message. `core/failures.py` preserves its
existing import API through this pure-data catalog; importing the catalog does
not import Qt. The 100 language entries were extracted and checked against
`g_lang` in the pinned whisper.cpp commit. No remote language lookup occurs.

Both palettes use a 10-point Segoe UI base font and layout-based sizing.
`tools/render_gui.py` starts a separate Qt process for each theme and scale,
setting QT_SCALE_FACTOR before QApplication. The Windows offscreen plugin has
no font enumeration in this environment. For headless parity, the theme loads
Segoe UI from the installed Windows fonts when the font database is empty.
No font file is copied, redistributed or downloaded. Rendering fails if its
Latin glyph check fails. QFontDatabase.addApplicationFont was verified with the
installed binding and [Qt documentation](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QFontDatabase.html).

Screenshots use synthetic recording names and progress, not processing evidence.
Actual processing and event-loop timing are tested separately with public
fixtures. Outputs stay in ignored build storage and are uploaded as a draft
release for review.

The WFP CI harness additionally starts the real Qt window via
`tests/offline/gui_batch.py`, completes a public-fixture batch through its
normal Start/worker path, and includes that process in the same zero-connection
audit window as self-test and headless batch. It runs only on the disposable
Windows CI host; local smoke runs do not change firewall or audit settings.

## Test data confinement

The approved real backend_probe cleanup was completed before M3. An audit hook
installed when conftest loads rejects audited Python file and directory access
to the real Dusty app-data root. Every test also receives a repo-local
LOCALAPPDATA, inherited by its subprocesses. The guard test deliberately tries
protected operations against an unused temporary root and verifies rejection
before any file is created. GUI tests inject RuntimePaths rooted inside the
repository. No real app settings are used for tests or screenshots.

## PM screenshot review corrections

Options is a modal dialog with live choices, saved when it closes; the main
window never inserts or expands a settings panel. Text/Word remain on the main
screen; other persisted formats are under More formats. Move actions use a
right-click menu and Alt+Up/Alt+Down. Translation help appears only for an
incompatible selected Translate task. Row and bottom phase labels share one
formatter, including initial zero-progress preparation.

Collision/error/summary names are shown as plain text in the UI, never logged.
Collision radio buttons retain an explicit safe choice, and summaries show
nonzero counts and each failed recording's reason. A Qt Fusion proxy style
paints clear check/radio indicators; stylesheet control boundaries use measured
sRGB contrast. Regression tests inspect actual painted borders for check/radio,
push/tool buttons, combo/spin boxes, text entry, table and scroll area in both
themes. Native operating-system file pickers remain subject to desktop review.
