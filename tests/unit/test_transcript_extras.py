"""Time markers and words that may be wrong in TXT and DOCX, shared by both platforms."""

import io
import json
import math
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from docx import Document

from dusty import devcli
from dusty.core import BatchOptions, Job, Segment, Transcript, Word
from dusty.engine.whisper import parse_whisper_json
from dusty.export import TextExtras, render_docx, render_json, render_srt, render_txt, render_vtt
from dusty.export.formats import UNSURE_CUTOFFS, UNSURE_NOTE
from dusty.queue.outputs import write_outputs
from dusty.queue.storage import load_batch, save_batch, save_settings
from dusty.runtime_paths import RuntimePaths

ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "tests/fixtures/exports"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CREATED = datetime(2026, 10, 22, tzinfo=UTC)


def transcript(*segments: Segment, language: str = "en") -> Transcript:
    end = max((segment.end for segment in segments), default=0.0)
    return Transcript(segments, language, "transcribe", "small", "cpu", end)


def words(*pairs: tuple[str, float]) -> tuple[Word, ...]:
    return tuple(Word(text, confidence) for text, confidence in pairs)


def segment(index: int, start: float, end: float, text: str, *pairs) -> Segment:
    return Segment(index, start, end, text, words(*pairs))


def engine_json(tmp_path: Path, parts: list[dict]) -> Path:
    path = tmp_path / "raw.json"
    path.write_text(
        json.dumps({"result": {"language": "en"}, "transcription": parts}), encoding="utf-8"
    )
    return path


def part(text: str, tokens: object, start: int = 0, end: int = 1000) -> dict:
    return {"offsets": {"from": start, "to": end}, "text": text, "tokens": tokens}


def token(text: str, p: object) -> dict:
    return {"text": text, "p": p}


def parse(path: Path) -> Transcript:
    return parse_whisper_json(
        path, model_id="small", task="transcribe", backend="cpu", duration_sec=1.0
    )


# Engine output


def test_parser_groups_tokens_into_words_with_their_lowest_confidence(tmp_path) -> None:
    tokens = [
        token("[_BEG_]", 0.9),
        token(" Fai", 0.13),
        token(",", 0.02),
        token(" pa", 0.9),
        token("pa", 0.6),
        token(".", 0.99),
        token("[_TT_50]", 0.5),
    ]
    result = parse(engine_json(tmp_path, [part(" Fai, papa.", tokens)]))
    assert result.segments[0].words == (Word(" Fai,", 0.13), Word(" papa.", 0.6))
    assert result.segments[0].text == " Fai, papa."


def test_parser_reads_the_real_engine_fixture_into_words_matching_its_text() -> None:
    result = parse(ROOT / "tests/fixtures/engine/sample-output.json")
    segment = result.segments[0]
    assert segment.words
    assert "".join(word.text for word in segment.words).split() == segment.text.split()
    assert all(0 <= word.confidence <= 1 for word in segment.words)


@pytest.mark.parametrize(
    "tokens",
    [
        None,
        "not a list",
        [token(" Hello", "0.5")],
        [token(" Hello", True)],
        [token(" Hello", 1.5)],
        [token(" Hello", -0.1)],
        [token(" Hello", math.nan)],
        [{"p": 0.5}],
        ["text"],
        [token(" Goodbye", 0.9)],
    ],
)
def test_parser_keeps_plain_text_when_tokens_are_missing_or_unexpected(tmp_path, tokens) -> None:
    raw = part(" Hello", tokens)
    if tokens is None:
        del raw["tokens"]
    path = tmp_path / "raw.json"
    path.write_text(
        json.dumps({"result": {"language": "en"}, "transcription": [raw]}), encoding="utf-8"
    )
    result = parse(path)
    assert result.segments[0].text == " Hello" and result.segments[0].words == ()


def test_parser_treats_each_token_as_a_word_in_scripts_without_spaces(tmp_path) -> None:
    tokens = [token("北京", 0.2), token("欢迎", 0.9), token("你", 0.95), token("。", 0.4)]
    result = parse(engine_json(tmp_path, [part("北京欢迎你。", tokens)]))
    assert [word.text for word in result.segments[0].words] == ["北京", "欢迎", "你", "。"]
    assert result.segments[0].words[-1].confidence == 1.0


def test_parser_keeps_persian_words_whole(tmp_path) -> None:
    tokens = [token(" سلام", 0.4), token(" دن", 0.9), token("یا", 0.3)]
    result = parse(engine_json(tmp_path, [part(" سلام دنیا", tokens)]))
    assert result.segments[0].words == (Word(" سلام", 0.4), Word(" دنیا", 0.3))


# Options


def test_batch_options_keep_extras_off_by_default() -> None:
    options = BatchOptions("tiny", Path("out"))
    assert not options.time_markers and not options.mark_unsure
    assert options.marker_minutes == 5.0 and options.unsure_level == "very"


@pytest.mark.parametrize(
    "changes",
    [
        {"marker_minutes": 0.4},
        {"marker_minutes": 120.5},
        {"marker_minutes": math.nan},
        {"marker_minutes": math.inf},
        {"marker_minutes": True},
        {"marker_minutes": "5"},
        {"unsure_level": "maybe"},
        {"time_markers": 1},
        {"mark_unsure": "yes"},
    ],
)
def test_batch_options_refuse_invalid_extras(changes) -> None:
    with pytest.raises(ValueError):
        BatchOptions("tiny", Path("out"), **changes)


@pytest.mark.parametrize("minutes", [0.5, 5, 5.4, 120])
def test_batch_options_accept_whole_and_decimal_minutes(minutes) -> None:
    assert BatchOptions("tiny", Path("out"), marker_minutes=minutes).marker_minutes == minutes


def test_extras_turn_minutes_into_whole_seconds_and_levels_into_cut_offs() -> None:
    extras = TextExtras.choose(
        time_markers=True, marker_minutes=5.4, mark_unsure=True, unsure_level="somewhat"
    )
    assert extras == TextExtras(324, UNSURE_CUTOFFS["somewhat"])
    assert TextExtras.choose(
        time_markers=False, marker_minutes=5.4, mark_unsure=False, unsure_level="very"
    ) == TextExtras(None, None)
    assert UNSURE_CUTOFFS["very"] < UNSURE_CUTOFFS["somewhat"]


# Plain files stay exactly as before


def plain_transcript() -> Transcript:
    # The transcript the plain-docx fixtures were rendered from by 1.1.3 (7c3fe7a).
    return Transcript(
        (
            segment(0, 0, 1, "  Hello  world. ", ("  Hello", 0.01), ("  world. ", 0.01)),
            Segment(1, 3, 4, "سلام دنیا"),
            Segment(2, 400, 401, "<b> & later"),
        ),
        "en",
        "transcribe",
        "tiny",
        "cpu",
        401,
    )


@pytest.mark.parametrize("extras", [None, TextExtras()])
def test_extras_off_write_the_1_1_3_docx_and_txt(extras) -> None:
    payload = render_docx(
        plain_transcript(), Path("sample.wav"), created_utc=CREATED, extras=extras
    )
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert (
            archive.read("word/document.xml") == (EXPORTS / "plain-docx-document.xml").read_bytes()
        )
        assert archive.read("word/styles.xml") == (EXPORTS / "plain-docx-styles.xml").read_bytes()
    assert render_txt(plain_transcript(), extras) == (
        "Hello world.\r\n\r\nسلام دنیا\r\n\r\n<b> & later\r\n".encode()
    )


def test_captions_and_json_never_change_with_extras(tmp_path) -> None:
    source = tmp_path / "clip.wav"
    job = Job(source)
    base = BatchOptions("tiny", tmp_path / "plain", formats=("srt", "vtt", "json"))
    extra = BatchOptions(
        "tiny",
        tmp_path / "extra",
        formats=("srt", "vtt", "json"),
        time_markers=True,
        marker_minutes=0.5,
        mark_unsure=True,
        unsure_level="somewhat",
    )
    for options in (base, extra):
        write_outputs(job, options, plain_transcript())
    for suffix in ("srt", "vtt"):
        plain = (tmp_path / "plain" / f"clip.{suffix}").read_bytes()
        assert (tmp_path / "extra" / f"clip.{suffix}").read_bytes() == plain
    assert render_srt(plain_transcript()) == (tmp_path / "extra/clip.srt").read_bytes()
    assert render_vtt(plain_transcript()) == (tmp_path / "extra/clip.vtt").read_bytes()
    first, second = (
        json.loads((tmp_path / folder / "clip.json").read_text(encoding="utf-8"))
        for folder in ("plain", "extra")
    )
    assert first["segments"] == second["segments"]
    assert "[?]" not in json.dumps(second, ensure_ascii=False)
    assert render_json(plain_transcript(), source, created_utc=CREATED)


# Time markers


def timed(*starts_and_texts: tuple[float, str]) -> Transcript:
    return transcript(
        *(Segment(i, start, start + 1, text) for i, (start, text) in enumerate(starts_and_texts))
    )


def txt_lines(value: Transcript, extras: TextExtras) -> list[str]:
    return render_txt(value, extras).decode("utf-8").split("\r\n\r\n")


def test_markers_fall_at_each_interval_and_show_the_real_time() -> None:
    value = timed(
        (0, "Start."),
        (1, "Still talking."),
        (299, "Before."),
        (302.4, "After five."),
        (303, "Same paragraph."),
        (601, "Ten."),
    )
    assert txt_lines(value, TextExtras(marker_sec=300)) == [
        "Start. Still talking.",
        "Before.",
        "[00:05:02]",
        "After five. Same paragraph.",
        "[00:10:01]",
        "Ten.\r\n",
    ]


def flowing(step: float, *starts_and_texts: tuple[float, str]) -> Transcript:
    """Speech without pauses: each segment lasts until the next one starts."""
    return transcript(
        *(Segment(i, start, start + step, text) for i, (start, text) in enumerate(starts_and_texts))
    )


def test_marker_waits_for_a_sentence_to_end_but_not_for_long() -> None:
    waits = flowing(5, (290, "One sentence"), (295, "goes on"), (300, "and on"), (305, "until."))
    waits = transcript(*waits.segments, Segment(4, 310, 311, "Next one."))
    assert txt_lines(waits, TextExtras(marker_sec=300))[-2:] == ["[00:05:10]", "Next one.\r\n"]
    gives_up = flowing(10, (290, "No"), (300, "end"), (310, "in"), (320, "sight"), (330, "at"))
    assert txt_lines(gives_up, TextExtras(marker_sec=300)) == [
        "No end in sight",
        "[00:05:30]",
        "at\r\n",
    ]


def test_marker_uses_a_pause_as_a_break() -> None:
    value = timed((290, "No"), (291, "end"), (310, "after a pause"))
    assert txt_lines(value, TextExtras(marker_sec=300)) == [
        "No end",
        "[00:05:10]",
        "after a pause\r\n",
    ]


def test_marker_respects_closing_quotes_after_a_sentence() -> None:
    value = timed((299, '"Fie, papa," said she, "it is natural."'), (300.5, "Then she left."))
    assert txt_lines(value, TextExtras(marker_sec=300))[1] == "[00:05:00]"


def test_short_intervals_wait_less_for_a_sentence() -> None:
    value = flowing(5, (25, "No"), (30, "end"), (35, "yet"), (40, "here"))
    assert txt_lines(value, TextExtras(marker_sec=30)) == ["No end yet", "[00:00:40]", "here\r\n"]


def test_a_long_silence_gets_one_marker_not_one_per_interval() -> None:
    value = timed((10, "Before."), (1000, "After the silence."))
    assert txt_lines(value, TextExtras(marker_sec=60)) == [
        "Before.",
        "[00:16:40]",
        "After the silence.\r\n",
    ]


def test_recording_shorter_than_the_interval_has_no_marker() -> None:
    value = timed((0, "Hello."), (1, "Bye."))
    assert render_txt(value, TextExtras(marker_sec=300)) == render_txt(value)


def test_empty_transcript_stays_empty_with_extras() -> None:
    assert render_txt(transcript(), TextExtras(300, 0.5)) == b""
    document = Document(
        io.BytesIO(render_docx(transcript(), Path("x.wav"), extras=TextExtras(300, 0.5)))
    )
    assert UNSURE_NOTE not in [paragraph.text for paragraph in document.paragraphs]


# Words that may be wrong


def unsure_transcript() -> Transcript:
    return transcript(
        segment(
            0,
            0,
            2,
            ' "Fai, papa," said she.',
            (' "Fai,', 0.13),
            (' papa,"', 0.6),
            (" said", 0.99),
            (" she.", 0.98),
        ),
        Segment(1, 2.5, 3, " No words here."),
    )


def test_unsure_words_get_a_mark_before_their_punctuation() -> None:
    lines = txt_lines(unsure_transcript(), TextExtras(unsure_below=0.5))
    assert lines == [UNSURE_NOTE, '"Fai [?], papa," said she. No words here.\r\n']
    lines = txt_lines(unsure_transcript(), TextExtras(unsure_below=0.7))
    assert lines[1] == '"Fai [?], papa [?]," said she. No words here.\r\n'


def test_note_is_written_even_when_no_word_is_marked() -> None:
    value = timed((0, "Clear speech."))
    assert txt_lines(value, TextExtras(unsure_below=0.5)) == [UNSURE_NOTE, "Clear speech.\r\n"]


def test_marking_keeps_text_and_spacing_otherwise_unchanged() -> None:
    marked = render_txt(unsure_transcript(), TextExtras(unsure_below=0.5)).decode("utf-8")
    plain = render_txt(unsure_transcript()).decode("utf-8")
    assert marked.split("\r\n\r\n", 1)[1].replace(" [?]", "") == plain
    assert "  " not in marked


def test_markers_and_marks_together() -> None:
    value = transcript(
        Segment(0, 0, 1, "Hello."),
        segment(1, 301, 302, " Saint Pol.", (" Saint", 0.9), (" Pol.", 0.2)),
    )
    assert txt_lines(value, TextExtras(300, 0.5)) == [
        UNSURE_NOTE,
        "Hello.",
        "[00:05:01]",
        "Saint Pol [?].\r\n",
    ]


def test_a_mark_at_the_end_of_a_segment_is_not_the_end_of_a_sentence() -> None:
    pairs = ((" Nous", 0.9), (" sommes", 0.9), (" allés", 0.9), (" à", 0.9))
    value = transcript(
        segment(0, 290, 300.5, " Nous sommes allés à Locmariaquer", *pairs, (" Locmariaquer", 0.2)),
        Segment(1, 301, 306, " et ensuite au port."),
        Segment(2, 306, 310, " Puis la mer."),
    )
    plain = txt_lines(value, TextExtras(300))
    marked = txt_lines(value, TextExtras(300, 0.5))
    assert plain == [
        "Nous sommes allés à Locmariaquer et ensuite au port.",
        "[00:05:06]",
        "Puis la mer.\r\n",
    ]
    assert marked[1:] == [
        "Nous sommes allés à Locmariaquer [?] et ensuite au port.",
        "[00:05:06]",
        "Puis la mer.\r\n",
    ]


# Word documents


def docx_parts(value: Transcript, extras: TextExtras) -> tuple[list, bytes]:
    payload = render_docx(value, Path("talk.wav"), created_utc=CREATED, extras=extras)
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        xml = archive.read("word/document.xml")
    return Document(io.BytesIO(payload)).paragraphs, xml


def test_docx_markers_are_headings_and_the_next_paragraph_drops_its_time() -> None:
    value = timed((0, "Hello."), (100, "Later."), (301, "After."), (310, "Next."))
    paragraphs, _ = docx_parts(value, TextExtras(marker_sec=300))
    assert [(p.text, p.style.name) for p in paragraphs[2:]] == [
        ("[00:00:00] Hello.", "Normal"),
        ("[00:01:40] Later.", "Normal"),
        ("00:05:01", "Heading 2"),
        ("After.", "Normal"),
        ("[00:05:10] Next.", "Normal"),
    ]


def test_docx_marks_unsure_words_with_a_highlight_and_a_note() -> None:
    paragraphs, xml = docx_parts(unsure_transcript(), TextExtras(unsure_below=0.5))
    assert paragraphs[2].text == UNSURE_NOTE and paragraphs[2].style.name == "Dusty Note"
    body = paragraphs[3]
    assert body.text == '[00:00:00] "Fai [?], papa," said she. No words here.'
    highlighted = [run.text for run in body.runs if run.font.highlight_color is not None]
    assert highlighted == ["Fai"]
    assert xml.count(b'<w:highlight w:val="yellow"/>') == 1


def test_docx_unsure_persian_word_keeps_right_to_left_runs_in_schema_order() -> None:
    value = transcript(
        segment(0, 0, 1, " سلام دنیا", (" سلام", 0.2), (" دنیا", 0.9)), language="fa"
    )
    _, xml = docx_parts(value, TextExtras(unsure_below=0.5))
    assert b"<w:bidi/>" in xml
    assert (
        b'<w:rPr><w:rFonts w:cs="Arial"/><w:highlight w:val="yellow"/><w:rtl/></w:rPr>'
        b'<w:t xml:space="preserve">\xd8\xb3\xd9\x84\xd8\xa7\xd9\x85</w:t>' in xml
    )


def test_docx_with_extras_declares_its_styles() -> None:
    payload = render_docx(timed((301, "After.")), Path("a.wav"), extras=TextExtras(300, 0.5))
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        styles = archive.read("word/styles.xml")
    assert b'w:styleId="Heading2"' in styles and b'<w:outlineLvl w:val="1"/>' in styles
    assert b'w:styleId="DustyNote"' in styles


# Saved queues, settings and outputs


def test_queues_saved_by_1_1_3_load_with_extras_off(tmp_path) -> None:
    state = tmp_path / "queue.json"
    save_batch(state, BatchOptions("tiny", tmp_path / "out"), [Job(tmp_path / "a.wav")])
    data = json.loads(state.read_text(encoding="utf-8"))
    for key in ("time_markers", "marker_minutes", "mark_unsure", "unsure_level"):
        del data["options"][key]
    state.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_batch(state)
    assert loaded is not None
    options = loaded[0]
    assert not options.time_markers and not options.mark_unsure


def test_queues_keep_chosen_extras(tmp_path) -> None:
    state = tmp_path / "queue.json"
    chosen = BatchOptions(
        "tiny",
        tmp_path / "out",
        time_markers=True,
        marker_minutes=5.4,
        mark_unsure=True,
        unsure_level="somewhat",
    )
    save_batch(state, chosen, [Job(tmp_path / "a.wav")])
    loaded = load_batch(state)
    assert loaded is not None and loaded[0] == chosen


@pytest.mark.parametrize(
    "bad", [{"marker_minutes": 0}, {"marker_minutes": "5,4"}, {"unsure_level": "all"}]
)
def test_settings_refuse_invalid_extras(tmp_path, bad) -> None:
    with pytest.raises(ValueError):
        save_settings(tmp_path / "settings.json", {"schema_version": 1, **bad})
    assert not (tmp_path / "settings.json").exists()


def test_written_files_follow_the_batch_choices(tmp_path) -> None:
    value = transcript(
        Segment(0, 0, 1, "Hello."),
        segment(1, 330, 331, " Tiznit.", (" Tiznit.", 0.4)),
    )
    options = BatchOptions(
        "tiny",
        tmp_path / "out",
        formats=("txt", "docx"),
        time_markers=True,
        marker_minutes=5.4,
        mark_unsure=True,
    )
    write_outputs(Job(tmp_path / "talk.wav"), options, value)
    text = (tmp_path / "out/talk.txt").read_bytes().decode("utf-8")
    assert text.split("\r\n\r\n") == [UNSURE_NOTE, "Hello.", "[00:05:30]", "Tiznit [?].\r\n"]
    document = Document(str(tmp_path / "out/talk.docx"))
    assert "00:05:30" in [paragraph.text for paragraph in document.paragraphs]


# Development command line


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    seen: dict[str, list] = {"batch": []}
    paths = RuntimePaths(tmp_path / "bin", tmp_path / "models", ROOT / "resources", tmp_path / "u")
    monkeypatch.setattr(devcli, "resolve_paths", lambda: paths)
    monkeypatch.setattr(devcli, "probe_vulkan", lambda *a: False)

    class Coordinator:
        def __init__(self, *args):
            pass

        def run_batch(self, jobs, options, **kwargs):
            seen["batch"].append(options)
            return jobs

    monkeypatch.setattr(devcli, "Coordinator", Coordinator)
    source = tmp_path / "in/clip.wav"
    source.parent.mkdir()
    source.write_bytes(b"RIFF public fixture stand-in")
    seen["argv"] = ["transcribe", str(source), "--out", str(tmp_path / "out"), "--format", "txt"]
    return seen


def test_devcli_passes_extras_to_the_batch(cli) -> None:
    devcli.main([*cli["argv"], "--marker-minutes", "5.4", "--mark-unsure", "somewhat"])
    options = cli["batch"][0]
    assert options.time_markers and options.marker_minutes == 5.4
    assert options.mark_unsure and options.unsure_level == "somewhat"
    devcli.main(cli["argv"])
    assert not cli["batch"][1].time_markers and not cli["batch"][1].mark_unsure


@pytest.mark.parametrize("minutes", ["0.1", "121", "nan", "inf"])
def test_devcli_refuses_an_invalid_interval_with_a_code(cli, capsys, minutes) -> None:
    assert devcli.main([*cli["argv"], "--marker-minutes", minutes]) == 2
    captured = capsys.readouterr()
    assert captured.out.strip().splitlines()[-1] == "MARKER_MINUTES_INVALID"
    assert "Traceback" not in captured.out + captured.err and cli["batch"] == []
