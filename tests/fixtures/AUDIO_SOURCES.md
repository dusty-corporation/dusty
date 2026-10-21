# Audio fixture sources

## JFK speech excerpt

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

No Owner recording is stored here.
