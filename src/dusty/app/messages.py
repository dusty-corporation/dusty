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
CLEAR = "Clear queue"
START = "Start"
CANCEL_CURRENT = "Cancel current file"
CANCEL_ALL = "Cancel all"
OPTIONS = "Options"
ADVANCED = "Advanced"
OUTPUT = "Save transcripts to"
CHOOSE_FOLDER = "Choose folder"
NO_OUTPUT = "Choose where to save your transcripts"
SAME_FOLDER = "Save next to each recording"
KEEP_STRUCTURE = "Keep folder structure"
FORMATS = {
    "txt": "Text (TXT)",
    "docx": "Word (DOCX)",
    "srt": "Captions (SRT)",
    "vtt": "Captions (VTT)",
    "json": "JSON",
}
MODEL = "Accuracy and speed"
MODEL_NAMES = {
    "large-v3-turbo-q8_0": "Large v3 Turbo",
    "small": "Small",
    "medium": "Medium",
    "small.en": "Small English",
    "tiny": "Tiny",
}
RECOMMENDED = "{name} (Recommended)"
MISSING_RECOMMENDATION = "{name} is recommended but is not installed. Choose an installed model."
NO_MODELS = "No verified models are installed. Model downloads will be available in Model Manager."
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
    "This unfinished batch used {model}, which is not installed. "
    "Choose an installed option to continue."
)
USE_INSTALLED = "Use {model} for this batch"
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
SLOW = (
    "Without a compatible graphics processor this model will likely take longer than "
    "the recording itself."
)
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
SUMMARY = "Batch finished"
SUMMARY_COUNTS = "{done} done, {failed} failed, {skipped} skipped, {cancelled} cancelled"
DISMISS = "Done"
RETRY = "Retry failed files"
OPEN_FOLDER = "Open output folder"
OPEN_RESULT = "Open folder"
COLLISION_TITLE = "A transcript already exists"
COLLISION_HELP = "Choose what to do with existing transcripts. Your recording will be kept."
APPLY_ALL = "Use this choice for all remaining files in this batch"
CONTINUE = "Continue"
STOP_BATCH = "Cancel batch"
RESUME_TITLE = "Resume unfinished batch?"
RESUME_HELP = (
    "You have an unfinished batch ({count} files remaining). Completed files will be kept."
)
RESUME = "Resume"
DISCARD = "Discard batch"
WELCOME_TITLE = "Welcome to Dusty"
WELCOME_HELP = "Drop recordings, press Start, and get text and Word documents."
WELCOME_BUTTON = "Choose output folder and continue"
SYNC_TITLE = "This folder may sync to the cloud"
SYNC_HELP = (
    "This folder syncs to the cloud. Transcripts saved here may be uploaded by your "
    "sync service. Continue or choose another folder."
)
SYNC_CONTINUE = "Continue with this folder"
CLOSE_TITLE = "Stop and save this batch?"
CLOSE_HELP = (
    "The current file will stop. You can resume unfinished files the next time you open Dusty."
)
CLOSE_CONFIRM = "Stop and save"
KEEP_WORKING = "Keep working"
CLOSING = "Stopping safely..."
ERROR_TITLE = "Dusty needs your attention"
PREPARATION_ERROR = (
    "Dusty could not prepare transcription. Check the installed files and try again."
)
SAVE_ERROR = "Dusty could not save your settings. Choose a writable folder and try again."
SCAN_ERROR = "Dusty could not read this folder. Check access and try again."
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
    "queued": "Queued",
    "preflight": "Checking",
    "decoding": "Preparing audio",
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
UNFINISHED_NOTICE = "Your unfinished batch is saved."


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
        "Dusty could not decode this recording.", "Try converting it to MP3 or WAV."
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
