"""Plain-language failure explanations and recovery actions, without user data."""

from dataclasses import dataclass

from dusty.core.types import FailureCode

APP_NAME = "Dusty"
FILE_FILTER = (
    "Recordings (*.mp3 *.m4a *.aac *.wav *.flac *.ogg *.oga *.opus *.wma *.webm *.mp4 "
    "*.m4v *.mov *.mkv *.avi *.3gp *.amr)"
)
PRIVACY_TITLE = "Privacy and accuracy"
ABOUT_VERSION = "Dusty {version}"
TAGLINE = "Private transcription that never leaves your computer."
PRIVACY = (
    "Dusty processes your recordings entirely on this computer. After installation, it "
    "never needs an internet connection, and it never sends your audio or transcripts "
    "anywhere."
)
ACCURACY = (
    "Automatic transcripts can contain mistakes, especially with names, medications, "
    "and numbers. Always review a transcript before relying on it for medical, legal, "
    "or other important decisions."
)
DROP = "Drop recordings or folders here"
DROP_HELP = "Add one recording or a whole folder."
ADD_FILES = "Add files"
ADD_FOLDER = "Add folder"
REMOVE = "Remove"
MOVE_UP = "Move up"
MOVE_DOWN = "Move down"
CLEAR = "Clear list"
START = "Start"
ADD_RECORDINGS_FIRST = "Add recordings to start."
START_RUNNING = "A transcription is in progress."
SELF_TEST_RUNNING = "Checking the transcription model..."
CANCEL_CURRENT = "Cancel current file"
CANCEL_ALL = "Cancel all"
OPTIONS = "Options..."
OPTIONS_TITLE = "Options"
MORE_FORMATS = "More formats"
ADVANCED = "Advanced"
OUTPUT = "Save transcripts to"
CHOOSE_FOLDER = "Choose folder"
NO_OUTPUT = "Not chosen yet"
CHOOSE_OUTPUT_FIRST = "Choose where to save transcripts first."
CHOOSE_OUTPUT_MENU = "Choose where to save transcripts..."
CLEAR_FINISHED = "Clear finished"
EVERYTHING_DONE = "Everything in the list is done. Add more recordings to start again."
WAITING_CHOICE = "Waiting for your choice"
TRANSLATE_UNAVAILABLE = "Translate to English (unavailable)"
TRANSLATE_REASON = (
    "This choice cannot translate to English. "
    "Choose a multilingual option that supports translation."
)
SAME_FOLDER = "Save next to each recording"
KEEP_STRUCTURE = "Keep folder structure"
FORMATS = {
    "txt": "Text (TXT)",
    "docx": "Word (DOCX)",
    "srt": "Captions (SRT)",
    "vtt": "Captions (VTT)",
    "json": "JSON",
}
MODEL = "Transcription model"
MODEL_NAMES = {
    "large-v3-turbo-q8_0": "Large v3 Turbo: Best quality",
    "small": "Small: Balanced, all languages",
    "small.en": "Small English: Balanced, English only",
    "tiny": "Tiny: Fastest",
    "medium": "Medium: Translates to English",
}
MODEL_DETAILS = {
    "large-v3-turbo-q8_0": "Recommended with a graphics card",
    "small": "Small. Good on any computer",
    "small.en": "Small English. Good for English recordings on any computer",
    "tiny": "Lower accuracy",
    "medium": "Slower",
}

RECOMMENDED = "{name}, recommended"
MISSING_RECOMMENDATION = "The recommended model, {name}, is not installed yet."
NO_MODELS = "Download a transcription model first."
MANAGE_MODELS = "Manage models"
MANAGE_LATER = "Additional model downloads are not available yet."
CANCEL = "Cancel"
LANGUAGE = "Spoken language"
AUTO_LANGUAGE = "Auto-detect language"
TASK = "What to do"
TASKS = {"transcribe": "Transcribe", "translate": "Translate to English"}
TRANSLATE_DISABLED = (
    "This choice can transcribe, but cannot translate. Choose Medium to translate to English."
)
USE_MEDIUM = "Use Medium instead"
MISSING_BATCH_MODEL = (
    "Your unfinished recordings used {model}, which is not installed. "
    "Choose an installed option to continue."
)
USE_INSTALLED = "Use {model} for these recordings"
PROMPT = "Vocabulary hints (optional)"
PROMPT_HELP = "Names, medications, acronyms, separated by commas"
PROMPT_EXAMPLE = "For example: Dr. Rahimi, metformin, HbA1c"
PROMPT_WARNING = "These hints may exceed the available space. Put the most important words first."
COLLISION = "When a transcript already exists"
COLLISIONS = {"ask": "Ask me", "keep_both": "Keep both", "skip": "Skip", "overwrite": "Overwrite"}
DEVICE = "Processing device"
DEVICES = {"auto": "Automatic", "vulkan": "Graphics card", "cpu": "Processor only"}
DEVICE_HELP = (
    "Automatic uses a compatible graphics card, with the processor available as a fallback."
)
THREADS = "Processor threads"
THREADS_HELP = "More threads use more processor capacity. The default suits most computers."
VAD = "Skip silent parts"
VAD_HELP = "Voice detection reduces invented words during silence. Recommended on."
SLOW = "This model will be slow on this computer. For faster results, choose Balanced."
PREPARING = "Preparing..."
PREPARING_HELP = (
    "Checking installed choices and preparing graphics. First-time setup may take about 13 seconds."
)
READY = "Ready when you are"
ESTIMATING = "Estimating time remaining..."
ETA = "About {time} remaining"
FILE_COUNT = "File {current} of {total}"
SCAN_COUNT = (
    "{added} files added, {unsupported} unsupported files skipped, {duplicates} duplicates skipped"
)
SCANNING = "Finding recordings..."
SUMMARY = "All done"
SUMMARY_ITEMS = {
    "done": "{count} done",
    "failed": "{count} failed",
    "skipped": "{count} skipped",
    "cancelled": "{count} cancelled",
}
FAILED_FILES = "Recordings that could not finish"
NAMED_FAILURE = "{name}: {reason}"
RECORDING_NAME = "Recording: {name}"
EXISTING_TRANSCRIPT = "Existing transcript: {name}"
COLLISION_CHOICES = {
    "keep_both": "Keep both (the new one gets a number)",
    "overwrite": "Replace the old transcript",
    "skip": "Skip this recording",
}
DISMISS = "Done"
RETRY = "Retry failed files"
OPEN_FOLDER = "Open folder with transcripts"
OPEN_RESULT = "Open folder"
COLLISION_TITLE = "A transcript already exists"
COLLISION_HELP = "Choose what to do with existing transcripts. Your recording will be kept."
APPLY_ALL = "Use this choice for all remaining recordings"
CONTINUE = "Continue"
STOP_BATCH = "Stop"
RESUME_TITLE = "Pick up where you left off?"
RESUME_HELP = "You have {count} recordings left to finish. Completed transcripts will be kept."
RESUME = "Resume"
DISCARD = "Start over"
WELCOME_TITLE = "Welcome to Dusty"
WELCOME_HELP = "Drop recordings, press Start, and get text and Word documents."
WELCOME_BUTTON = "Choose output folder and continue"
SYNC_TITLE = "This folder may sync to the cloud"
SYNC_HELP = (
    "This folder syncs to the cloud. Transcripts saved here may be uploaded by your "
    "sync service. Continue or choose another folder."
)
SYNC_CONTINUE = "Continue with this folder"
CLOSE_TITLE = "Stop and save your progress?"
CLOSE_HELP = (
    "The current file will stop. You can resume unfinished files the next time you open Dusty."
)
CLOSE_CONFIRM = "Stop and save"
KEEP_WORKING = "Keep working"
CLOSING = "Stopping safely..."
ERROR_TITLE = "Dusty needs your attention"
PREPARATION_ERROR = "Dusty could not prepare transcription."
SAVE_ERROR = "Dusty could not save your settings."
SCAN_ERROR = "Dusty could not read this folder."
NO_FORMATS = "Choose at least one output format."
OK = "OK"
INCLUDE_SUBFOLDERS = "Include subfolders"
FOLDER_TITLE = "Add a folder of recordings"
THEME = "Appearance"
THEMES = {"system": "Follow Windows", "light": "Light", "dark": "Dark"}
FILE_MENU = "File"
TOOLS_MENU = "Tools"
HELP_MENU = "Help"
EXIT = "Exit"
CLEAR_HISTORY = "Clear history"
SELF_TEST = "Run self-test"
SELF_TEST_OK = "Dusty's self-test passed."
SELF_TEST_ERROR = "Dusty's self-test did not pass. Check your installed choices and try again."
ABOUT = "About Dusty"
EMPTY_CELL = ""
UNKNOWN_TIME = "--"
TIME = "{minutes}:{seconds:02}"
PERCENT = "{value}%"
CHOICES_SUMMARY = "{model}, {language}, {device}"
HEADERS = ("Recording", "Duration", "Status", "Progress", "Elapsed", "Result")
STATUSES = {
    "queued": "Waiting",
    "preflight": "Preparing",
    "decoding": "Preparing",
    "transcribing": "Transcribing",
    "exporting": "Saving",
    "done": "Done",
    "failed": "Failed",
    "cancelled": "Cancelled",
    "skipped": "Skipped",
}
GPU_FALLBACK = "Completed on processor (graphics card failed)"
GPU_NOTICE = (
    "The graphics card could not finish a file. Dusty completed it with the processor instead."
)
UNFINISHED_NOTICE = "Your unfinished recordings are saved."


def time_label(seconds: float) -> str:
    value = max(0, int(seconds))
    return TIME.format(minutes=value // 60, seconds=value % 60)


@dataclass(frozen=True)
class FailureMessage:
    message: str
    action: str


FAILURE_MESSAGES: dict[FailureCode, FailureMessage] = {
    FailureCode.NOT_FOUND: FailureMessage(
        "The recording could not be found.", "Add the file again."
    ),
    FailureCode.UNREADABLE: FailureMessage(
        "Dusty cannot read this recording.", "Check file access and try again."
    ),
    FailureCode.EMPTY_FILE: FailureMessage(
        "This recording is empty.", "Choose a recording that contains audio."
    ),
    FailureCode.NO_AUDIO: FailureMessage(
        "This file doesn't contain any audio we can transcribe.", "Choose an audio recording."
    ),
    FailureCode.DECODE_ERROR: FailureMessage(
        "Dusty could not decode this recording.",
        "This file may be damaged. If it plays in another program, try saving it again as WAV.",
    ),
    FailureCode.UNSUPPORTED_FORMAT: FailureMessage(
        "Dusty can't read this file type.", "Try converting it to MP3 or WAV."
    ),
    FailureCode.DISK_FULL: FailureMessage(
        "Not enough free disk space.", "Free up disk space and retry."
    ),
    FailureCode.MODEL_MISSING: FailureMessage(
        "The selected model is not installed.", "Open Model Manager to download it."
    ),
    FailureCode.MODEL_CORRUPT: FailureMessage(
        "The selected model is damaged.", "Open Model Manager to download it again."
    ),
    FailureCode.ENGINE_ERROR: FailureMessage(
        "Transcription could not complete.", "Click Retry or choose another model."
    ),
    FailureCode.ENGINE_CRASH: FailureMessage(
        "Transcription stopped unexpectedly.",
        "Click Retry. If it keeps happening, switch Processing device to CPU in Advanced settings.",
    ),
    FailureCode.GPU_ERROR: FailureMessage(
        "The graphics card could not process this file.", "Retry with Processing device set to CPU."
    ),
    FailureCode.OUTPUT_UNWRITABLE: FailureMessage(
        "Dusty could not save the transcript.", "Choose a writable output folder and retry."
    ),
    FailureCode.OUTPUT_EXISTS_SKIPPED: FailureMessage(
        "An existing transcript was kept.",
        "Choose Keep both or explicitly choose Overwrite to retry.",
    ),
    FailureCode.INTERNAL_ERROR: FailureMessage(
        "Dusty could not complete this file.", "Click Retry. If it happens again, restart Dusty."
    ),
}


LANGUAGES = (
    ("en", "English"),
    ("zh", "Chinese"),
    ("de", "German"),
    ("es", "Spanish"),
    ("ru", "Russian"),
    ("ko", "Korean"),
    ("fr", "French"),
    ("ja", "Japanese"),
    ("pt", "Portuguese"),
    ("tr", "Turkish"),
    ("pl", "Polish"),
    ("ca", "Catalan"),
    ("nl", "Dutch"),
    ("ar", "Arabic"),
    ("sv", "Swedish"),
    ("it", "Italian"),
    ("id", "Indonesian"),
    ("hi", "Hindi"),
    ("fi", "Finnish"),
    ("vi", "Vietnamese"),
    ("he", "Hebrew"),
    ("uk", "Ukrainian"),
    ("el", "Greek"),
    ("ms", "Malay"),
    ("cs", "Czech"),
    ("ro", "Romanian"),
    ("da", "Danish"),
    ("hu", "Hungarian"),
    ("ta", "Tamil"),
    ("no", "Norwegian"),
    ("th", "Thai"),
    ("ur", "Urdu"),
    ("hr", "Croatian"),
    ("bg", "Bulgarian"),
    ("lt", "Lithuanian"),
    ("la", "Latin"),
    ("mi", "Maori"),
    ("ml", "Malayalam"),
    ("cy", "Welsh"),
    ("sk", "Slovak"),
    ("te", "Telugu"),
    ("fa", "Persian"),
    ("lv", "Latvian"),
    ("bn", "Bengali"),
    ("sr", "Serbian"),
    ("az", "Azerbaijani"),
    ("sl", "Slovenian"),
    ("kn", "Kannada"),
    ("et", "Estonian"),
    ("mk", "Macedonian"),
    ("br", "Breton"),
    ("eu", "Basque"),
    ("is", "Icelandic"),
    ("hy", "Armenian"),
    ("ne", "Nepali"),
    ("mn", "Mongolian"),
    ("bs", "Bosnian"),
    ("kk", "Kazakh"),
    ("sq", "Albanian"),
    ("sw", "Swahili"),
    ("gl", "Galician"),
    ("mr", "Marathi"),
    ("pa", "Punjabi"),
    ("si", "Sinhala"),
    ("km", "Khmer"),
    ("sn", "Shona"),
    ("yo", "Yoruba"),
    ("so", "Somali"),
    ("af", "Afrikaans"),
    ("oc", "Occitan"),
    ("ka", "Georgian"),
    ("be", "Belarusian"),
    ("tg", "Tajik"),
    ("sd", "Sindhi"),
    ("gu", "Gujarati"),
    ("am", "Amharic"),
    ("yi", "Yiddish"),
    ("lo", "Lao"),
    ("uz", "Uzbek"),
    ("fo", "Faroese"),
    ("ht", "Haitian Creole"),
    ("ps", "Pashto"),
    ("tk", "Turkmen"),
    ("nn", "Nynorsk"),
    ("mt", "Maltese"),
    ("sa", "Sanskrit"),
    ("lb", "Luxembourgish"),
    ("my", "Myanmar"),
    ("bo", "Tibetan"),
    ("tl", "Tagalog"),
    ("mg", "Malagasy"),
    ("as", "Assamese"),
    ("tt", "Tatar"),
    ("haw", "Hawaiian"),
    ("ln", "Lingala"),
    ("ha", "Hausa"),
    ("ba", "Bashkir"),
    ("jw", "Javanese"),
    ("su", "Sundanese"),
    ("yue", "Cantonese"),
)


def summary_counts(jobs_counts: dict[str, int]) -> str:
    return ", ".join(
        SUMMARY_ITEMS[key].format(count=value) for key, value in jobs_counts.items() if value
    )


def phase_text(status: str, progress: float) -> str:
    return PREPARING if status == "transcribing" and progress == 0 else STATUSES[status]


ADDED_ONE = "1 recording added"
ADDED_MANY = "{count} recordings added"
UNSUPPORTED_ONE = "1 unsupported file skipped"
UNSUPPORTED_MANY = "{count} unsupported files skipped"
DUPLICATE_ONE = "{name} is already in the list"
DUPLICATE_MANY = "{count} recordings were already in the list"


def scan_summary(added: int, unsupported: int, duplicates: int, name: str = "") -> str:
    parts = []
    if added:
        parts.append(ADDED_ONE if added == 1 else ADDED_MANY.format(count=added))
    if unsupported:
        parts.append(
            UNSUPPORTED_ONE if unsupported == 1 else UNSUPPORTED_MANY.format(count=unsupported)
        )
    if duplicates:
        parts.append(
            DUPLICATE_ONE.format(name=name)
            if duplicates == 1 and name
            else DUPLICATE_MANY.format(count=duplicates)
        )
    return "; ".join(parts)


MODEL_MANAGER = "Transcription models"
MODEL_TECHNICAL = {
    "tiny": "Tiny",
    "small": "Small",
    "small.en": "Small English",
    "medium": "Medium",
    "large-v3-turbo-q8_0": "Large v3 Turbo",
    "silero-vad": "Silero VAD",
}
VOICE_MODEL = "Voice detection"
VOICE_DETAILS = "Voice detection. Required when Skip silent parts is on."
MANAGER_HEADERS = ("Model", "Best for", "Size", "Status")
MODEL_STATUSES = {
    "installed": "Installed",
    "not_installed": "Not installed",
    "damaged": "Damaged",
    "downloading": "Downloading",
}
DOWNLOAD = "Download"
DOWNLOAD_AGAIN = "Download again"
CANCEL_DOWNLOAD = "Cancel download"
DELETE_MODEL = "Delete"
VERIFY_ALL = "Verify all"
VERIFYING_MODELS = "Checking the downloaded files..."
VERIFYING_DOWNLOAD = "Checking the download..."
FREE_SPACE = "Free space for models: {gb:.1f} GB"
FREE_SPACE_UNKNOWN = "Free space for models is unavailable."
MODEL_SIZE = "{value:.1f}\u00a0{unit}"
MEGABYTES = "MB"
GIGABYTES = "GB"
DOWNLOAD_NAMES_JOIN = " and "
DOWNLOAD_PROGRESS = "{done} of {total}"
DOWNLOADING_MODEL = "Downloading {name}"
DOWNLOAD_TITLE = "Download transcription files?"
DOWNLOAD_CONFIRM = "Download {names} from github.com ({size})?"
DELETE_TITLE = "Delete this downloaded model?"
DELETE_CONFIRM = "Delete {name}? You can download it again later."
DELETE_SELECTED = (
    "Delete {name}? It is the model chosen in Options. You can download it again later."
)
DELETE_VOICE = (
    "Delete {name}? Skip silent parts is on, so Start will be unavailable until "
    "you download it again or turn off Skip silent parts in Options. "
    "You can download it again later."
)
CHOOSE_MODEL = "Choose a transcription model in Options."
MODEL_PLACEHOLDER = "Choose a transcription model"
NO_MODEL_SELECTED = "No model selected"
DOWNLOAD_RECOMMENDED = "Download recommended model ({name})"
DOWNLOAD_VOICE = "Download voice detection"
MODEL_REVIEW = "All models can make mistakes. Review transcripts before relying on them."
MODEL_QUALITY = {
    "large-v3-turbo-q8_0": "Best quality",
    "small": "Balanced, all languages",
    "small.en": "Balanced, English only",
    "medium": "Translates to English",
    "tiny": "Fastest",
    "silero-vad": 'Needed for "Skip silent parts"',
}
MODEL_NOTE = {
    "large-v3-turbo-q8_0": "Recommended with a graphics card",
    "small": "Works on any computer. May make more mistakes.",
    "small.en": "Works on any computer. May make more mistakes.",
    "medium": "Slower",
    "tiny": "Lowest accuracy. Good for quick drafts.",
    "silero-vad": "Small download",
}
MODEL_BEST_FOR = dict(
    zip(
        ("large-v3-turbo-q8_0", "small", "small.en", "medium", "tiny", "silero-vad"),
        (
            "Everyday use",
            "Any computer",
            "English recordings",
            "Translation",
            "Quick drafts",
            "Skipping silence",
        ),
        strict=True,
    )
)
MODELS_READY = "Your downloaded models have been checked."
DOWNLOAD_FINISHED = "The download is complete and verified."
DOWNLOAD_PAUSED = "Download cancelled. The partial download was removed."
MODEL_DELETED = "The downloaded model was deleted."
DOWNLOAD_IT = "Download it"
VAD_MISSING = "Download voice detection first, or turn off Skip silent parts in Options."
FETCH_ERRORS = {
    "INVALID": "The download details could not be read.",
    "BLOCKED": "The download address is not allowed.",
    "MISMATCH": "The download is damaged. Download it again.",
    "DISK_FULL": "There is not enough free space for this download.",
    "NETWORK": "The download could not finish. Check your connection and try again.",
    "IO": "Dusty could not save the downloaded file.",
    "BUSY": "Another download is already using this file.",
    "START_FAILED": "The downloader could not start. Check the installed files.",
    "PROTOCOL": "The downloader did not finish correctly. Try the download again.",
    "DELETE": "The downloaded model could not be deleted.",
}
