# Child process and crash-report boundaries

Reviewed 2026-10-25 against Microsoft API documentation:

- https://learn.microsoft.com/en-us/windows/win32/api/errhandlingapi/nf-errhandlingapi-seterrormode
- https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information
- https://learn.microsoft.com/en-us/windows/win32/api/werapi/nf-werapi-weraddexcludedapplication
- https://learn.microsoft.com/en-us/windows/win32/api/werapi/nf-werapi-werremoveexcludedapplication
- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/abort

SEM_NOGPFAULTERRORBOX and DIE_ON_UNHANDLED_EXCEPTION mitigate ordinary unhandled
crashes. They do not establish that CRT abort/fail-fast is WER-silent. Earlier
per-user observation used the redirected test profile and was not evidence about
the actual Windows store. Re-review N-1/N-5 correct that claim.

ADR 0027 approves exactly five basename exclusions under the current user only.
Setup calls WerAddExcludedApplication with False before probing; failed registration
stops Setup. ReviewOnly cannot register. Uninstall calls WerRemoveExcludedApplication
with False for only those names after its data helper finishes. Cancel before
file installation rolls back only new entries. No HKLM writes or global disabling.

The installed CI acceptance compiles a tiny release /MD MSVC fixture which calls
abort without modifying _CALL_REPORTFAULT, or starts an unmanaged faulting thread.
It runs both modes under each of the five names in the actual guarded Job Object.
The native fixture is generated under pytest temp, never build/bin, bundled, cached
as native input, or redistributed. The real store roots are captured in conftest
before LOCALAPPDATA redirection. The native child gets the real environment too.
Six standard areas (user/machine ReportQueue, ReportArchive, Temp) are checked.
Unreadable/enumeration failures fail the check. A final 30-second observation
bounds the no-new-report result; it does not prove custom stores, future delayed
reports, administrator collectors or all Windows policies. Only the explicitly
enabled disposable hosted CI step can run it. Never run it on an Owner machine.

run_job_process allows only sys.executable, resolved dusty-fetch, or binaries
under the app bin root. It refuses linked executable paths and foreign cwd.
The audit hook and literal static check block documented socket/delegation/DLL
routes, with PE and WFP gates as separate layers. These are defense in depth,
not a hostile-code sandbox; direct arbitrary native calls remain outside Python
audit coverage. No product code uses the identified escape routes.


The pinned Inno runtime is PE32 (the build gate verifies this). Its WER import
uses the absolute Windows {syswow64}/wer.dll with loadwithalteredsearchpath,
not a DLL beside Setup or in its launch folder. Windows supplies the DLL; none
is bundled. [Inno 6 DLL imports](https://jrsoftware.org/is6help/topic_scriptdll.htm)
confirm filename constants and the dependency-search flag (reviewed 2026-10-25).


## Inno uninstall completion

Pinned 4adf37ed7f3fd2bd11c6836ba056e3de170fbabf,
Projects/Src/Setup.Uninstall.pas: RunFirstPhase returns when the second phase sends
WM_KillFirstPhase from DeleteUninstallDataFiles. The second phase then waits for
that launcher, delays for self-deletion, and only later calls usPostUninstall.
Waiting for the launcher alone is not proof that WER exclusion cleanup finished.
CI 40237902530 exposed this race after its real WER test passed.

Both CI uninstall callers now retain and wait for the actual child process tree
within their original deadlines, including the known _unins.tmp worker's exit
code. They do not sleep until a desired registry state appears. Exact registry
assertions run only after process completion. A harmless two-process regression
proves a launcher exit cannot bypass a still-running post-work child. There is
no product cleanup change or weakened registry assertion.


The full integration suite keeps real pinned-archive/license and native self-test
entry-point checks in tests/integration/test_native_acceptance.py. Their bodies
are unchanged from the earlier unit location. Private automatic source jobs
run asset-independent units only; public/manual full suites retain both checks.
