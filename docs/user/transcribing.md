# Transcribe recordings or a folder

1. Use **Add files**, **Add folder**, or drop recordings onto the window. For a
   folder, choose whether to include subfolders. Unsupported files are counted
   and skipped. A recording already in the list is highlighted, not added twice.
2. Use **Choose folder...** and check the **Saving to** destination. A long path
   is shortened in the middle; point at it to see the full path. A sync-folder warning
   means another program may upload the transcripts. Choose a local folder if
   that would be inappropriate. If saving next to each recording is on, change
   it in Options to choose one destination folder. No folder is chosen automatically.
3. Open **Options...**. Choose the model, spoken language and **Transcribe** or
   **Translate to English**. Choose Text and/or Word on the main window; captions
   and JSON are under **More formats** in Options. Keep **Skip silent parts** on
   unless you have a reason to turn voice detection off.
4. Review the list. Select a row to Remove it. Right-click for Move up/Move down;
   their keyboard shortcuts are shown in the menu. Arrow keys change rows; Tab
   leaves the list. Clearing the list does not delete recordings.
5. Press **Start**. Dusty prepares, transcribes and saves one recording at a time.
   The bottom status follows the current recording. You can cancel the current
   recording or all remaining work. Closing during a run offers to stop and save
   your progress for the next launch.
6. In **All done**, open the folder with transcripts, or retry failed recordings.
   If none succeeded, use Done and read the plain failure reasons. Use
   **Clear finished** or add more recordings for another run.

## Existing transcripts

Keep recordings and transcripts outside Dusty's own app and data folders. Dusty
will ask you to choose another folder if you select one it manages. If an older
saved destination points there, your files are kept in place and Dusty asks for
a new destination. It does not move or delete them.

When a transcript already existed before the run, Dusty names it and asks whether
to keep both, replace the old transcript, or skip that recording. You can apply
the choice to remaining recordings. **Stop** stops the run. Two different
recordings with the same name added to one run get numbered outputs automatically.

## After saving

Read the transcript before relying on it. Check names, numbers and medical terms
against the recording. A Word document contains a title, a subtitle and paragraphs
with time prefixes. Captions contain approximate time ranges, not a
guarantee of word-perfect timing. Translate to English is automatic translation;
it is not a replacement for an interpreter in important conversations.
