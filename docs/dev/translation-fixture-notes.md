# Persian translation fixture

The public-domain LibriVox bilingual Rubaiyat recording alternates Persian
and English. The introduction is longer than initially assumed. Aligning
the following English readings with Whinfield's published 1883 quatrains
locates Persian quatrain 2 at source interval [107, 122) seconds. Its English
reading starts at approximately 122 seconds and is excluded from the fixture.

The 15-second fixture is documented and hashed in
`tests/fixtures/AUDIO_SOURCES.md`. Transcribe produces Persian script, whereas
Translate produces English, including the independently published
reference keyword "fire". The automated test requires at least 20 Persian
characters in the Transcribe control, no Persian characters in Translate,
the reference keyword, additional independent source content, and at least
four distinct English function words.
This is the specified loose translation smoke test, not a translation
accuracy benchmark. Neither expected text nor keywords come from model output.

Tiny did not retain the reference keyword reliably. Small passed locally and
in one CI run but failed on other hosted runners. The test now uses Medium,
the PM's already approved translation recommendation in ADR 0016. It retains
the original keyword requirement and adds a second source-content check.
No decoding flags or temperature fallback behavior were changed for this test.

Dev/CI fetch includes `medium-f16` from the existing published models-v1
manifest in addition to Tiny, Small.en, and Silero VAD, with the existing
SHA-256 checks. Medium replaces Small in the dev test set; the V1 catalog
and models-v1 release are unchanged. The extra model is 1,533,763,059 bytes.
There is no new conversion or dependency. See ISSUE-008 for the CI evidence.
