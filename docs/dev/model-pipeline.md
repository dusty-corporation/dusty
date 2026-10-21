# M1 model conversion pipeline

The approved `models.yml` workflow pins openai/whisper to commit
`86098128c0b4f24f0e2aa2994de830614b474227` and whisper.cpp to
`d1be6fde11ac6e0407606b4e42fe72d34add8037`. Each candidate runs
in its own Linux matrix job. The source checkpoint URL and SHA-256 come
from the pinned OpenAI source. The job removes the `.pt` file after
conversion and before quantization. Each conversion and quantization
runs twice, and mismatched hashes fail the job.

Each completed model uploads directly to the draft `models-v1` release;
only small manifest fragments pass between jobs as Actions artifacts. A
final job combines them into `models.json`. A size check rejects any file
of 2 GiB or more. The Silero 6.2.3 wheel contains its JIT weights locally;
conversion opens that local resource under a network-blocking
`sitecustomize.py` process.

Run [39691863874](https://github.com/dusty-corporation/dusty/actions/runs/39691863874)
completed all 11 model jobs and the manifest job. It uploaded ten
transcription candidates and Silero VAD. The workflow scans the captured
converter log and runs the repository model-host policy checker. The
complete 5,472,012-byte CI log was also downloaded and scanned locally
with the checker's `PATTERN`; it had zero matches.

The release remains a draft. Phase B uses the files and SHA-256 values in
its `models.json`; it does not require the original `.pt` files.
