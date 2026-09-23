# Preparing a release

Run these commands sequentially from the project directory, with the documented
AVR toolchain. GCC's LTO temporary files are shared: do not run simultaneous builds.

```powershell
.\build.ps1
python tools/stages.py
python tools/report.py
python tools/package.py
python tools/verify_release.py
```

Use the same Python 3 interpreter for all commands. `build.ps1 -Python PATH`
selects an explicit interpreter for the first step. `make zip` is an alternative
for environments with GNU make.

The ZIP contains sources, documentation, third-party notices and only the final
bootloader's ELF/HEX/MAP and size reports. It excludes compiler caches, device
provisioning records, hardware logs, intermediate firmware and research clones.
`dist/SHA256SUMS.txt` checks the archive; `SHA256SUMS.json` inside checks its files.
Archive verification checks hashes, rebuilds in a temporary directory and compares
the HEX byte for byte. Temporary verification directories are removed afterwards.

Before publishing:

1. Confirm Flash <=8192 bytes and load addresses within 0x3E000–0x3FFFF.
2. Check [LICENSES.md](../LICENSES.md), the source snapshot hashes and runtime notices.
3. Publish the ZIP and checksum together, with source matching the binary.
4. State the actual test status. Host models are not board validation. See the
   physical test matrix in [TESTING.md](TESTING.md).
5. Do not include `build/provision/`: S/N and MAC records belong to individual units.
6. Version 1.0.0 starts a new history without the removed upstream headers.
   Use the matching-source ZIP and do not redistribute earlier development archives
   as the current release. See LICENSES.md.

CI downloads Arduino AVR-GCC `7.3.0-atmel3.6.1-arduino7` for x86_64 Linux from
`downloads.arduino.cc`, verifies SHA256
`bd8c37f6952a2130ac9ee32c53f6a660feb79bee8353c8e289eb60fdcefed91e`
(Arduino package index checked 2026-09-23), then builds and verifies the release.
The compiler itself is not included in uploaded artifacts. Artifacts contain
the complete matching-source ZIP and checksum, including runtime license notices.

This workflow prepares local artifacts; it does not create a repository or upload
anything to GitHub. Development format v1 may change; do not imply migration support.

Python is resolved from `-Python` or PATH (`python`, `python3`, `py`); no editor
runtime is required. AVR tools are resolved from `AVR_PREFIX`, PATH or the Arduino
tool installation in the current user's profile.

Build outputs use relative project paths. DWARF keeps source line information with
the project root mapped to `.` and the toolchain root to `/avr-toolchain`; MAP uses
`<avr-toolchain>`. These logical paths may need debugger source-path substitution
on another machine. Packaging rejects files containing the current workspace or
home path, including binary debug information. This is a path privacy check, not
a general secret scanner.
