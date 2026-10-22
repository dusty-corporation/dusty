"""Plain-language failure explanations and recovery actions, without user data."""

from dataclasses import dataclass

from .types import FailureCode


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
        "The selected model file is damaged.", "Open Model Manager to download it again."
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
