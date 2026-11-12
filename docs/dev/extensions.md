# Extension points

`src/dusty/extensions/__init__.py` lists what an extension can add to Dusty.
With no extension installed, every list is empty and Dusty behaves exactly as
Dusty 1.2.0 did. Byte for byte, that means it writes the same outputs, saved
queues and settings. `tests/unit/test_output_goldens.py` checks this against
files made from the 1.2.0 source.

## Loading

An extension is the one package named `EXTENSION_PACKAGE`. `loaded()` imports
it once and calls its `register(extensions)`. If the package is not
installed, Dusty runs with no extensions. Any other import error is raised.

`active()` returns the extensions Dusty uses. Tests choose others with
`use(...)`, and `use(Extensions())` is Dusty without any.

## Points

| Point | Shared code that uses it | When empty |
| --- | --- | --- |
| `options`: check boxes in Options | `app/window.py` (form, settings, summary, start rules), `core/types.py` (`BatchOptions.extension_options`), `queue/storage.py`, `devcli.py` (one `--key` flag each) | No box, no settings key, no saved queue key, no flag |
| `stages`: steps after transcription, before the outputs are written | `queue/coordinator.py` | Transcripts go straight to export, as in 1.2.0 |
| `decorations`: paragraph and caption labels, extra JSON fields | `queue/outputs.py`, `export/formats.py` | No labels, no extra fields |
| `actions`: context menu entries for a finished file of this session | `app/window.py` (context menu, double click), `queue/outputs.py` (`rewrite_outputs`) | No extra menu entry |
| `models`: extra model files, each with its own catalog file in `resources` | `models/catalog.py`, `models/registry.py` (`extra_path`), `app/model_manager.py`, `app/workers.py`, `dusty_fetch/downloader.py`, the app builds | The model manager lists the 1.2.0 models only |
| `helpers`: extension programs, started like the engine | `runtime_paths.py` (`resolve_helper_command`), `platform/process.py` (`approved_executable`) | Only the 1.2.0 programs may be started |
| `engine_hints`: a prompt for the engine while an option is on, for some languages, when the user gave no hints | `queue/coordinator.py` (`engine_prompt`), `engine/whisper.py` (`carry_prompt`) | The engine gets the user's prompt as in 1.2.0 |
| `about`: lines About shows after the version | `app/window.py` (`show_about`), `app/dialogs.py` (`AboutDialog`) | About is as in 1.2.0 |
| `commands`: Help menu entries | `app/window.py` (menus) | The Help menu is as in 1.2.0 |

## Rules for extensions

- A stage gets the job's WAV, the transcript, its verified model, the thread
  count, cancel and progress. It returns a transcript. Values it adds go in
  `annotations` on segments and on the transcript, never in new fields of the
  shared types.
- A stage that fails raises `StageFailed` with a fixed reason: no paths, no
  text. The file is still saved without what the stage adds, and the list
  shows the stage's `failed` text. If `cancelled` is set, the file is
  cancelled instead.
- Files a stage leaves in the job's owned work folder are listed in
  `work_files`, so cleanup removes them.
- An option's `unsupported` text may be a function: Options asks it again on
  every refresh, so the reason can change while Dusty runs.
- Settings and saved queues hold the keys of extension options under
  `extension_options`, only while an option is on, so an extension key can
  never collide with a core setting. A saved queue that names an option not
  installed or not supported here loads with that option off, and a stage
  whose option is not supported never runs.
- An extension model's catalog file has schema version 1, `"kind":
  "extension"` and one `models` entry. Its file name matches `dusty-*.onnx`.
  The downloader accepts that name only from such a file; the bundled manifest
  takes `ggml-*.bin` files only, as in 1.2.0. The model is verified by size
  and SHA-256 like every other model.
- `Job.transcript` is kept in memory for actions only when a stage added
  annotations.

## Helper programs in the app builds

`tools/helper_programs.py` reads `packaging/addons/programs.json` if it
exists. Public Dusty has no such file, so it builds, checks and installs
exactly the programs of 1.2.0. Each entry in the file describes one helper
program:

- its PyInstaller entry and module;
- its excludes, and the modules the GUI must leave out because only the
  program uses them;
- files to drop from its bundle;
- required and forbidden modules;
- a later macOS it may need;
- its smoke test module;
- its pinned Mac license texts and notice rows.

| Build file | What it does with each program |
| --- | --- |
| `packaging/dusty.spec`, `packaging/dusty-macos.spec` | A separate analysis and onedir, like dusty-fetch. The GUI analysis fails when public Dusty's GUI holds an add-on module, or any GUI holds a program's own modules. |
| `tools/build_macos_app.py` | Places it in `Contents/Helpers/<name>`, moves its data to `Contents/Resources/<name>`, and signs it as a bootloader. A program with a later macOS is left out of the app's minimum. |
| `tools/check_macos_bundle.py` | Checks its modules, macOS, runtime guard and unused files. Fails on add-on modules in a public GUI, and on helper folders it does not know. |
| `tools/macos_notices.py`, `tools/check_licenses.py` | Stage and verify its pinned texts under `licenses/macos/addons/`, and add its notice rows. |
| `tools/check_bundle.py`, `tools/check_bundle_version.py`, `tools/inventory_bundle.py` | Windows: console subsystem, offline dependencies, version and inventory. |
| `installer/generate_iss.py`, `tools/wer_observer.py`, `tools/test_installer.ps1`, `tools/offline_failure_diagnostics.ps1` | Windows Error Reporting exclusions after the five Dusty programs. |
| `tools/check_helper_programs.py` (CI) | Runs its smoke test and, on Windows, the offline PE import check. |

## Goldens

`tools/make_output_goldens.py` makes the goldens from a source tree. They were
made once from the 1.2.0 source (49f698e):

```bash
python tools/make_output_goldens.py --src <1.2.0 checkout>/src --resources <1.2.0 checkout>/resources --out tests/fixtures/goldens-1.2.0
```

Each DOCX entry carries the time it was written, so DOCX files are compared
entry by entry. Every other file is compared byte for byte.

A saved queue writes each file location with the separator of the computer, as
1.2.0 did, so `tests/fixtures/goldens-1.2.0/win32/queue.json` was made from the
1.2.0 source on Windows, with the same command. The settings scenario fixes the
default thread count at 4, because the default follows the computer's cores. On
Windows the settings file and all 40 outputs then match the goldens made on the
Mac, byte for byte (DOCX entry by entry).
