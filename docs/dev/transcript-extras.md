# Time markers and words that may be wrong

Owner request 2026-11-09, from a user who used Whisper Turbo from the command
line before Dusty; the design below is the one the Owner approved. Both options
are off by default, remembered, and change only TXT and DOCX. With both off,
TXT and DOCX are byte for byte what 1.1.3 wrote (tests compare against
`tests/fixtures/exports/plain-docx-*.xml`, rendered by 7c3fe7a).

## One shared change for Windows and Mac

Everything is shared code. The Windows engine (engine-v3) and the Mac engine
build the same whisper.cpp commit d1be6fd; their patches change only speech
detection timing and threads, not the `-ojf` JSON with token probabilities.
No native, installer or bundle change is needed.

| Layer | File |
| --- | --- |
| Word confidence from the engine JSON | `src/dusty/engine/whisper.py` (`_words`) |
| Types and batch options | `src/dusty/core/types.py` (`Word`, `BatchOptions`) |
| TXT and DOCX rendering | `src/dusty/export/formats.py` (`TextExtras`, `_blocks`) |
| Saved queues | `src/dusty/queue/storage.py` (older queues load with both off) |
| Options row and summary | `src/dusty/app/window.py` (`MinutesBox`), `messages.py` |
| Developer command line | `src/dusty/devcli.py` (`--marker-minutes`, `--mark-unsure`) |

## Words and confidence

Tokens that start with a space start a word; `[_...]` tokens are skipped. In
scripts written without spaces (Chinese, Japanese, Thai and similar) each token
is a word, so one unsure character never marks a whole sentence. The engine
already joins tokens that split one character. A word's confidence is the
lowest `p` of its tokens that contain a letter or digit; punctuation alone is
fully sure. If the tokens are missing, malformed or do not spell the segment
text, the segment keeps its plain text and nothing in it is marked.

A marked word gets " [?]" after its letters and before trailing punctuation:
`"Fai [?], papa,"`. In Word the word is also highlighted. When marking is on,
the file starts with "Words marked [?] may be wrong. Unmarked words can be
wrong too." even if no word is marked.

## Levels, not percentages

Per-word scores are weak evidence. Kuhn, Kersken and Zimmermann (2025,
arXiv 2503.15124) found that for Whisper about half the marks land on correct
words and about half the errors are missed; marking about 4% of words helped
people fix errors while 13 to 21% did not. Vertanen and Kristensson (CHI 2008)
found that marks make people miss unmarked errors. So Dusty shows marks only,
few by default, with honest help text.

Starting cut-offs (`UNSURE_CUTOFFS`): very unsure below 0.5, somewhat unsure
below 0.7. Measured on the M2 with Metal:

| Material | Model | Below 0.5 | Below 0.7 |
| --- | --- | --- | --- |
| 4 French sentences full of rare names, 84 words, 9 wrong | Turbo | 8 marked, 6 wrong | 17 marked, 7 wrong |
| 11 min public domain audiobook (bench/swineherd.mp3) | Turbo | 6 (0.4%), 1 wrong | 31 (2.1%), 3 wrong |
| same | Small | 26 (1.7%), 5 wrong | 64 (4.3%), 10 wrong |
| same | Tiny | 88 (5.8%), 28 wrong | 164 (10.8%), 46 wrong |

"Wrong" for the audiobook means not matching its checked reference text after
removing case, punctuation and hyphens; spelling style differences remain in
that count. Confident mistakes are never marked ("Disney" for Tiznit at 0.76),
and a correct rare name can score low ("Wojciechowski" at 0.12).

Open before release: tune the cut-offs per model on real recordings with
checked transcripts, ideally French interviews. Tiny marks too many words at
0.7, so the cut-offs will likely depend on the model.

## Time markers

The interval is typed in minutes, 0.5 to 120, with ".", "," or the computer's
own decimal separator (U+066B on Persian and Arabic systems, which also show
their own digits), and rounded to whole seconds (5.4 is 324 s). Markers go before the first
sentence or paragraph that starts at or after each multiple of the interval,
waiting at most 30 s, or a third of the interval if shorter. Whether a
sentence ended is read from the engine's plain text, never from text that
already carries a [?] mark. A marker shows the
real start of the text after it, so a player can jump there. A long silence
gets one marker, not one per interval. There is no marker at the start.

TXT: a line `[00:05:34]` on its own. DOCX: a Heading 2 paragraph `00:05:34`,
listed in Word's Navigation pane; the paragraph right under it omits its own
time prefix, which would repeat the heading. All other paragraphs keep theirs.

## Tests

`tests/unit/test_transcript_extras.py` (parser, rendering, options, saved
queues, settings, outputs, devcli) and `tests/unit/test_gui_transcript_extras.py`
(Options row, French decimal comma, invalid input, saved choices). All are
platform neutral and run in the Windows `checks` job and the Mac suite.
Person checks still open: the highlight and Navigation pane in Word on Windows
and Mac, and Pages.
