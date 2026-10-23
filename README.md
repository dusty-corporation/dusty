# Dusty

Dusty is a planned free, open-source, offline Windows transcription app using whisper.cpp. M0 provides the development foundation and an empty Qt window; transcription is not implemented yet.

See `docs/pm/SPEC.md` for the engineering plan.

## License

Dusty's own code is licensed under Apache-2.0. See [LICENSE](LICENSE) and
[NOTICE](NOTICE). The Owner, the sole contributor, authorized the change to
provide an explicit patent grant for future contributors. Third-party components
retain their own licenses and notices.
# Windows SmartScreen warning (unsigned draft builds)

Dusty's V1 installer is unsigned. Windows may show "Windows protected your PC".
After checking that you downloaded the expected build and its checksum, select
"More info", then "Run anyway". This warning reflects the lack of a paid code
signing certificate; it is not proof that a file is safe.

Verify the downloaded installer against the accompanying `SHA256SUMS.txt`:

```powershell
Get-FileHash .\Dusty-*-draft-unsigned.exe -Algorithm SHA256
```

Compare the entire hash with the entry for that exact filename. Stop if it differs.
Current installer artifacts are for review and clean-machine testing, not a
published release. The Owner controls publication.
