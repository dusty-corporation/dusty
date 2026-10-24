# M5 interim 11 - Registered installation protection

## Owner actions

Use public/synthetic files only in the disposable VM. .11/.12 are superseded
final candidates after the install-folder review. Do not publish them. The final
checklist will name .13/.14 after all gates pass. No Owner data was accessed.

## Finding and authorized repair

ISSUE-025 extends the already-approved NN-7 protection to Inno's registered-file
removal. The app-data helper alone could not protect private contents at an
installed filename. An isolated retention test failed; the native flow lacked
a preflight before automatic deletion. The new guarded read-only preflight stops
unsafe uninstall before any deletion, including silent mode. It needs no new
policy exception; normal uninstall remains unchanged.

71 focused tests pass. Native acceptance now must preserve synthetic private
bytes placed at the registered models.json filename, then restore the original
and pass the ordinary gates. A failed protection receipt blocks draft creation.
The repair continues under the existing ownership decision and explicit second
review assignment; no further Owner response is needed to implement it.
