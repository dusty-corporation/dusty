# Transcribe recordings or a folder

1. Use **Add files**, **Add folder**, or drop recordings onto the window. For a
   folder, choose whether to include subfolders. Unsupported files are counted
   and skipped. A recording already in the list is highlighted, not added twice.
   Adding a recording marked Done makes it Waiting again. Press Start to process
   it with your current settings; other finished recordings are left alone.
2. Use **Choose folder...** and check the **Saving to** destination. A long path
   is shortened in the middle; point at it to see the full path. A sync-folder warning
   means another program may upload the transcripts. Choose a local folder if
   that would be inappropriate. If saving next to each recording is on, change
   it in Options to choose one destination folder. No folder is chosen automatically.
3. Open **Options...**. Choose the model, spoken language and **Transcribe** or
   **Translate to English**. Choose Text and/or Word on the main window; captions
   and JSON are under **More formats** in Options. **Skip long silences** is off
   by default. It can save time on long pauses, but may miss quiet or distant
   speech. Leave it off for classroom questions or recordings made from far away.
   Time markers and marked words are optional; see
   [Time markers and words that may be wrong](#time-markers-and-words-that-may-be-wrong).
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

## Time markers and words that may be wrong

Two options in Options, under **In Text and Word files**, change only Text and
Word transcripts. Both are off until you turn them on, and Dusty remembers your
choice. Captions and JSON are never changed by them.

- **Add a time marker every** 5 **minutes** adds the time on its own line at
  about each interval, so you can find a moment in the recording. Type whole or
  decimal minutes from 0.5 to 120; 5.4 (or 5,4) means 5 minutes 24 seconds. A
  marker waits for the end of a sentence or a pause, at most 30 seconds, and
  shows the real time of the text that follows it. In Word the markers are
  headings, so they are listed in Word's Navigation pane.
- **Mark words that may be wrong** adds [?] after words Dusty is unsure of, and
  in Word also highlights them. Choose **Only very unsure words (fewer marks)**
  or **Also somewhat unsure words (more marks)**. The transcript then starts with
  a short note. This is a hint, not a check: some marked words are right, and
  some mistakes are not marked, so still read the whole transcript. If a name is
  often wrong, add it to [vocabulary hints](vocabulary.md) and transcribe again.

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
against the recording, marked or not. A Word document contains a title, a
subtitle and paragraphs with time prefixes. Captions contain approximate time ranges, not a
guarantee of word-perfect timing. Translate to English is automatic translation;
it is not a replacement for an interpreter in important conversations.
