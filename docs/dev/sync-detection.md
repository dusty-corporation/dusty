# Local sync-folder detection

OneDrive uses its three local environment roots; Dropbox reads local info.json
from APPDATA and LOCALAPPDATA. Existing profile Google Drive/My Drive folders
are retained as warning roots. No vendor service is contacted.

Google's [configuration reference](https://knowledge.workspace.google.com/admin/drive/advanced-drive-for-desktop-configuration?hl=en)
documents DefaultMountPoint as a drive letter or absolute path and Windows
policy, user and host registry locations. The read-only Windows helper honors
that precedence and expands environment variables. Google's
[troubleshooting guide](https://support.google.com/drive/answer/2565956?hl=en)
documents G: as the default streaming location. When no mount override exists,
the helper treats G: as a warning root only if local DriveFS data is present.
These sources were checked on 2026-10-22. Tests inject settings readers and
temporary directories; they never write the maintainer's registry or vendor data.

The detector does not parse undocumented account databases, enumerate network
volumes, or identify arbitrary mirrored folders selected inside a vendor app.
An old DriveFS cache with an unrelated G: drive can cause a conservative warning.
The warning is advisory and explicitly offers Continue. Detection cannot disable
another application's synchronization. See ISSUE-009 for the inherited gap.
