# Dusty on a Mac

Dusty for Mac needs a Mac with Apple silicon and macOS 13.3 or later.

## Install

Open the Dusty disk image (`Dusty-<version>-macos-arm64.dmg`). A window shows
Dusty next to your Applications folder. Drag Dusty onto the Applications folder,
then eject the disk image and open Dusty from Applications. Dusty does not need
an administrator password, and models are not in the disk image: you choose and
download one when Dusty first opens.
Install only a release from the official repository.

### The first time you open Dusty

Dusty is not signed by Apple yet, so the first time you open it macOS stops it
and says it could not verify Dusty. This is expected. To allow it:

1. Open Dusty from Applications. When macOS says Dusty was not opened, choose
   Done.
2. Open System Settings, then Privacy & Security. Scroll down to Security, where
   macOS says Dusty was blocked, and choose Open Anyway.
3. Choose Open Anyway again, and enter your password or use Touch ID if asked.

macOS remembers this, and Dusty then opens normally. You may need to do this
again after an upgrade. On a Mac that your organization manages, these settings
may be locked; ask your administrator to allow Dusty.

## First run

1. Choose **Choose output folder and continue** and pick where transcripts go.
2. Open **Manage models** in the **Tools** menu and download a model. Dusty
   asks before it downloads anything and checks each file before using it.
3. Add recordings and press **Start**.

With the Mac graphics processor working, Dusty recommends Large v3 Turbo for
transcription and Medium for translation. Tiny is the fastest, but with
**Skip long silences** off it can invent text during long silent parts.
**Skip long silences** is off by default, as on Windows. If you use Tiny for
recordings with long pauses, turn it on in Options before you press **Start**.

Inside a virtual Mac, Dusty uses the processor for everything, because the
graphics processor there lacks features the engine uses and is much slower.
The transcripts are the same.

Useful keys: Command+O adds files, Command+Shift+O adds a folder, Command+? opens
help and Command+Q quits. To reach every button with Tab, turn on Keyboard
navigation in System Settings, Keyboard.

## Where Dusty keeps its data

Settings, downloaded models, unfinished work and a short log without transcript
text are in `~/Library/Application Support/Dusty`. Your recordings and
transcripts stay where you put them.

If Dusty says its data folder is not safe to use, that folder is a link or
belongs to another user. Rename it in Finder and open Dusty again.

## Upgrade Dusty

Choose **Quit Dusty**, open the new disk image, drag Dusty onto Applications and
choose Replace. If macOS stops the new version, allow it as in The first time
you open Dusty. Settings, downloaded models and unfinished work are not inside
the app, so they are kept. Dusty checks each model again before using it, and a
model that still matches is not downloaded again. Your recordings and
transcripts are not touched.

## Remove Dusty

1. In the **Tools** menu choose **Remove Dusty data**. Leave the box for
   downloaded models checked to remove them too, or uncheck it to keep them in
   case you use Dusty again. Choose **Remove and quit**. Dusty quits and
   deletes its settings, queue history, logs and unfinished work. This cannot be
   undone. Your recordings and transcripts are never removed.
2. Drag Dusty from Applications to the Trash, then empty the Trash.

If Dusty says some data was kept, it found files in its data folder that it
could not confirm are its own, such as transcripts saved there. It leaves them
for you. To see them, in Finder choose Go, Go to Folder and enter
`~/Library/Application Support/Dusty`.

If you only drag Dusty to the Trash, settings and downloaded models stay and are
found again if you reinstall Dusty later.

macOS itself may keep a graphics shader cache and crash reports outside the
Dusty folder. The [privacy guide](../privacy.md) explains them.
