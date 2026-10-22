# Persian translation fixture

The public-domain LibriVox bilingual Rubaiyat recording alternates Persian
and English. The introduction is longer than initially assumed. Aligning
the following English readings with Whinfield's published 1883 quatrains
locates Persian quatrain 2 at source interval [107, 122) seconds. Its English
reading starts at approximately 122 seconds and is excluded from the fixture.

The 15-second fixture is documented and hashed in
`tests/fixtures/AUDIO_SOURCES.md`. Small Transcribe produces Persian script
(86 Persian characters and no ASCII letters in the local control), whereas
Small Translate produces English, including the independently published
reference keyword "fire". The automated test requires at least 20 Persian
characters in the Transcribe control, no Persian characters in Translate,
the reference keyword, and at least four distinct English function words.
This is the specified loose translation smoke test, not a translation
accuracy benchmark. Neither expected text nor keywords come from model output.

Tiny did not retain the reference keyword reliably, so this test uses the
already approved V1 multilingual Small model. Dev/CI fetch now includes
`small-f16` from the existing published models-v1 manifest in addition to
Tiny, Small.en, and Silero VAD, with the existing SHA-256 checks. There is no
new model conversion, dependency, or change to models-v1.
