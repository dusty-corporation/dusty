# Audio fixture sources

## JFK speech excerpt

`resources/selftest.wav` is a byte-identical copy of `audio/formats/jfk.wav`
for the offline installed-app self-test. It has the same public-domain
provenance and expected text below.

- Source: `samples/jfk.wav` from pinned whisper.cpp v1.9.5,
  https://github.com/ggml-org/whisper.cpp/blob/v1.9.5/samples/jfk.wav .
- Underlying work: President John F. Kennedy's 1961 inaugural address, a
  United States federal government work in the public domain.
- Duration: 11.000 seconds.
- Expected text: "And so, my fellow Americans, ask not what your country can
  do for you, ask what you can do for your country."
- `formats/jfk.wav` is the upstream sample. Every other file in `formats/`
  was generated from it once with FFmpeg 8.0.1 (Gyan full build) using
  `ffmpeg -i samples/jfk.wav -vn -c:a CODEC -f FORMAT formats/jfk.EXT`.
  The codec/format pairs are: mp3/libmp3lame/mp3, m4a/aac/ipod,
  aac/aac/adts, flac/flac/flac, ogg/libvorbis/ogg, oga/libvorbis/ogg,
  opus/libopus/opus, wma/wmav2/asf, webm/libopus/webm, mp4/aac/mp4,
  m4v/aac/mp4, mov/aac/mov, mkv/aac/matroska, avi/pcm_s16le/avi,
  3gp/aac/3gp, amr/libopencore_amrnb/amr. The AMR conversion additionally
  used `-ar 8000 -ac 1`.
- `bad/no-audio.mp4` is one second of generated black video with no audio:
  `ffmpeg -f lavfi -i color=c=black:s=16x16:r=1:d=1 -an -c:v libx264`.
  It contains no third-party recording. `bad/zero-byte.mp3` is empty.
  `bad/corrupt.mp3` is only the first 32 bytes of `formats/jfk.mp3`.
- `formats/تست ضبط.m4a` and the nested `long-path/.../jfk.m4a` are
  byte-identical copies of `formats/jfk.m4a` for path handling tests.
- `vad/mostly-silence-10min.m4a` is 600 seconds of generated silence
  mixed with two copies of the public-domain JFK clip, at 0 and 300
  seconds. It was made with FFmpeg 8.0.1 using `anullsrc`, `adelay=300000`,
  and `amix=inputs=3:duration=first`. Expected speech is the JFK sentence
  twice, with silence elsewhere.

## LibriVox benchmark chapter

- Source recording: "The Swineherd", read by Phil Chenevert for LibriVox,
  https://librivox.org/the-little-match-girl-by-hans-christian-andersen/ ,
  direct file
  https://archive.org/download/thelittlematchgirl_1311_librivox/thelittlematchgirl_02_andersen_128kb.mp3 .
- License: LibriVox recordings are public domain in the United States.
- Source text: Hans Christian Andersen, "The Swineherd", in Project
  Gutenberg eBook 1597, https://www.gutenberg.org/ebooks/1597 . Its text
  is public domain in the United States.
- Duration: 660.015601 seconds (11 minutes). Stored as
  `bench/swineherd.mp3`. The benchmark kit uses a 16 kHz mono PCM WAV
  derived from this file by the pinned minimal FFmpeg build.
- Expected text: the chapter in `bench/swineherd-reference.txt`. The
  LibriVox introduction and closing title were added. The German song
  and its footnote were represented by the spoken English translation.
  The reference was compared with a timestamped tiny-model transcript to
  locate the introduction, ending, and three song locations. Those
  model-derived spans are excluded from WER. The scored Gutenberg text
  and audio boundaries are specified in
  `bench/swineherd-scored-spans.json` and explained in
  the source-text scoring boundaries stored beside the fixture. No human listening pass is required
  for this source-text-only score under the PM's Phase B decision.

No private recording is stored here.

## Persian translation smoke fixture

- `audio/translate/rubaiyat-fa.wav`: 15 seconds, 16 kHz mono signed 16-bit
  PCM, 480,310 bytes; SHA-256
  `5c1ab7a657e78769eff8ab33f9afe4e58f7d38820eaada850649596b6be31c2a`.
- Recording: Omar Khayyam's Rubaiyat, Persian reader MostafaRazavi,
  [LibriVox bilingual edition](https://librivox.org/the-rubaiyat-of-omar-khayyam-version-2-by-omar-khayyam/),
  chapter 1, Quatrains 1-101. LibriVox explicitly declares its recordings
  public domain in the USA; the original poems are medieval.
- Source: https://archive.org/download/rubaiyat_bilingual_1207_librivox/rubaiyat_01_khayyam_whinfield_64kb.mp3
  SHA-256 `2ad5b8c9f30ee8540f1706b64257c7717b3b0bed6447163e34a547d6f9c9dc5e`.
- Excerpt: source interval [107, 122) seconds, Persian quatrain 2, excluding
  the following English reading. Transcribe with Medium recognizes Persian
  script; Translate produces English instead.
- maintainer-verified by listening on 2026-10-22: [107, 122) seconds contains a
  complete spoken Farsi quatrain.
- Independent reference: Edward Henry Whinfield's 1883 bilingual edition,
  [quatrain 2](https://archive.org/details/quatrains1883omaruoft), says
  "burns as fire". The test checks that keyword, another reference concept
  (brought/night/wind/air), English script and function words. It makes no WER
  or literary translation quality claim.
- Reproduce with the pinned minimal FFmpeg: `ffmpeg -nostdin -hide_banner
  -loglevel error -protocol_whitelist file,pipe -i <source.mp3> -ss 107 -t 15
  -ac 1 -ar 16000 -c:a pcm_s16le rubaiyat-fa.wav`.
