# Troubleshooting

| What you see | What to try |
|---|---|
| Start is disabled | Read the reason just above it. Choose an output folder, install or choose a model in Options, or add recordings. If everything is done, clear finished rows or add more recordings. |
| A recording is already in the list | Use the highlighted row. The same recording is not added twice. |
| Duration is `--` | Dusty could not determine the duration yet. This display alone does not mean the file is damaged. |
| Dusty could not decode a recording | It may be damaged. If it plays in another program, try saving it again as WAV. Keep the original. |
| There is no audio | Some video files have no audio track. Choose a recording with sound. |
| Not enough free disk space | Make room on both the models/work drive and the output drive, then retry. Temporary decoded audio also needs space. |
| A model is Damaged | Use Manage models > Download again. Do not use a model that fails verification. |
| A download fails | Check your connection and free space. Try the download again. After cancelling or closing Dusty, it starts fresh. Only approved GitHub HTTPS hosts are accepted. Enterprise proxy support is not implemented. |
| Graphics fails or seems stuck | In Options, choose Processor only, then retry. Automatic may already have completed the recording on the processor. Update graphics drivers through your normal trusted source if appropriate. |
| Translation is unavailable | Choose Medium. Turbo and English-only models cannot translate to English. |
| Names or numbers are wrong | Try vocabulary hints and review against the recording. A larger model may help but cannot guarantee correctness. |
| Self-test fails | Check installed models with Verify all, try Processor only, and note the plain error. Do not treat a failed installer self-test as a successful installation. |

For support, report the app version, Windows version, model, processing device,
steps and plain error. Do not upload confidential recordings, transcripts,
vocabulary hints, screenshots containing private names, or the settings/unfinished
work files. Those local JSON files can contain private paths and hints.
