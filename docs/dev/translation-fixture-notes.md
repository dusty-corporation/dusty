# Persian translation fixture research

Status: incomplete; no excerpt or expected translation has been accepted or
committed, and no translation acceptance claim is made.

LibriVox's [bilingual Rubaiyat recording](https://librivox.org/the-rubaiyat-of-omar-khayyam-version-2-by-omar-khayyam/)
lists Persian/Farsi and explicitly declares the recordings public domain in
the USA. Chapter 1 alternates Persian reader MostafaRazavi with English reader
NoelBadrian. Its [1883 source text](https://archive.org/details/quatrains1883omaruoft)
contains Persian and Whinfield's English translation and is marked not in
copyright by the archive.

Downloaded source, kept only in ignored build storage:

- URL: https://archive.org/download/rubaiyat_bilingual_1207_librivox/rubaiyat_01_khayyam_whinfield_64kb.mp3
- SHA-256: `2ad5b8c9f30ee8540f1706b64257c7717b3b0bed6447163e34a547d6f9c9dc5e`

The pinned CLI's `-dl` option exits after language detection (verified in
`examples/cli/cli.cpp` at the pinned commit). Ten-second windows at 20 and
80 seconds were detected as Persian, while many intervening windows were
English. Initial translations did not match the selected published-quatrain
keyword set. The exact poem boundaries and reference pairing must be resolved
before accepting a short fixture; language detection alone is insufficient.
The approved multilingual Small model was downloaded and hash-verified locally
for this research. Dev fetch's approved default set has not been changed.

Next: identify one complete Persian quatrain and its published English pairing,
trim a small audio excerpt, document provenance in AUDIO_SOURCES.md, and add
a translation keyword check. Do not include the English reading in the input.
