Dusty M1 benchmark kit

This folder runs on Windows 10/11 without Python, developer tools, or
administrator rights. Keep the full bin/cpu and bin/vulkan folders intact.
The DLLs beside each executable are required. The GPU driver supplies
vulkan-1.dll; do not copy the Vulkan SDK into this folder.

MODEL SETUP

Sign in to the Dusty GitHub repository and open its draft models-v1 release.
Download these ten files into this kit's models folder:

  ggml-tiny.bin
  ggml-base.bin
  ggml-small.bin
  ggml-small.en.bin
  ggml-medium.bin
  ggml-large-v3-turbo.bin
  ggml-large-v3-turbo-q8_0.bin
  ggml-large-v3-turbo-q5_0.bin
  ggml-large-v3-q8_0.bin
  ggml-large-v3-q5_0.bin

The script verifies every file against models.json before running it.
The Silero VAD model is not needed for this speed and WER benchmark.
All models are downloaded separately; none is bundled in the kit zip.

DESKTOP STEPS (Ryzen + RTX 3080 Ti)

1. Unzip the kit into a normal folder and download the models above.
2. Open Windows PowerShell in the kit folder. Run both public tests:

  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath .\audio\swineherd.wav -Backend cpu -Machine desktop -Threads 8 -PublicReference
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath .\audio\swineherd.wav -Backend vulkan -Machine desktop -Threads 8 -PublicReference

3. Prepare one real recording of about 10 minutes as 16 kHz mono PCM
   s16le WAV in a private folder outside this kit. If conversion is needed,
   use the bundled ffmpeg.exe and keep its output in that private folder:

  .\bin\ffmpeg\ffmpeg.exe -nostdin -hide_banner -loglevel error -protocol_whitelist file,pipe -i "C:\private\original.m4a" -vn -map 0:a:0 -ac 1 -ar 16000 -c:a pcm_s16le -f wav "C:\private\bench-input.wav"

4. Run the private WAV with both backends. Replace the example path only
   in your local command. The script does not copy it or save a transcript:

  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath "C:\private\bench-input.wav" -Backend cpu -Machine desktop -Threads 8
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\bench\run-bench.ps1 -AudioPath "C:\private\bench-input.wav" -Backend vulkan -Machine desktop -Threads 8

SURFACE LAPTOP 5 STEPS (i5-1235U + Iris Xe)

1. Copy the full kit and separately downloaded model files to the Surface.
2. Plug in the Surface and set Windows power mode to Best performance.
3. Open Windows PowerShell in the kit folder and run the same four commands
   above with -Machine surface and -Threads 4. For the two public commands,
   keep -PublicReference. For private commands, use the Surface's own local
   path to the same private WAV. Do not put it in this kit folder.

RESULTS AND BACKEND CHECK

Each command writes one CSV and Markdown summary under results/. Public
commands also write JSON transcripts for the public-domain chapter only.
Private commands write metrics only: model, quantization, backend,
threads, duration, wall time, real-time factor, peak memory, and CPU
variant. They do not store the recording's path, name, or content.

The packages include x64, SSE4.2, Sandy Bridge, Haswell, Skylake-X,
Cannon Lake, Cascade Lake, Ice Lake, and Alder Lake CPU backend DLLs.
The engine startup log line `load_backend: loaded CPU backend from ...
ggml-cpu-haswell.dll` identifies which variant was selected. The GPU
line `whisper_backend_init_gpu: using Vulkan0 backend` proves Vulkan was
actually used. `use gpu = 1` alone does not prove it. The CSV records the
parsed backend and CPU variant. If a run cannot identify its backend,
the script stops rather than guessing.

Send the CSV, Markdown summaries, and public-*.json files from results/
back to the implementing engineer. Do not send the private recording or
its converted WAV. WER is computed later with summarize_bench.py on the
public JSON and the included swineherd-reference.txt.
