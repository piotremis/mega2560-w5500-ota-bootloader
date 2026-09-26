# Contributing

This firmware has a hard **8192-byte** Flash limit. UART0/CH340 upload and W5500
OTA were tested successfully on hardware on 2026-09-22. Power-loss and fault
injection acceptance remain separate items. Describe the problem and expected behavior when opening an issue or PR;
include the board wiring, toolchain version and relevant test output.

## Development checks

Use a topic branch and open a pull request against `main`. Both `host-tests` and
`avr-release` must pass on an up-to-date branch. Merge with squash; direct pushes,
force pushes and branch deletion are blocked by the main protection policy.

Maintain project documentation in English. Use [docs/README.md](docs/README.md)
as the navigation index. Keep numeric limits consistent with code and distinguish
measured results from acceptance work. Edit `tools/report.py` for generated
memory-report wording; do not translate or reformat original third-party notices.

GitHub Actions runs host models and a pinned AVR-GCC 7.3.0 build on Ubuntu.
It checks ELF/HEX bounds, negative linker cases, C/C++ application integration
and a fresh rebuild of the release ZIP. CI does not certify hardware.

1. Build/test on Windows: `./build.ps1`. Elsewhere: `make all` then `make test`.
2. See [release instructions](docs/RELEASING.md) for source/ZIP verification.
3. For UART changes, run `python tests/avrdude.py` with Arduino avrdude installed
   on Windows. This exercises host C code, not a physical AVR.
4. For release changes, run `make stages`, `make zip`, then
   `python tools/verify_release.py` to rebuild the archive in a fresh directory.
5. Report Flash bytes, end address and static SRAM. Do not install intermediate
   stage images. Do not describe host tests as hardware tests.

Install optional formatters with `python -m pip install -r tools/requirements-dev.txt`.
Use clang-format 18.1.8 for project C/header files (including tests), and
`ruff format tools tests` for Python. Preserve the unmodified upstream `third_party/arduino-stk500v2/stk500boot.c`.
The small `src/command.h` and `tools/baseline/avr_cpunames.h` are project-authored
replacements, not upstream files. Do not reintroduce the removed upstream headers. Keep protocol lengths, byte order,
EEPROM commit order and Flash bounds explicit in reviews.

Avoid heap allocation, Arduino libraries and new buffers without a measured
budget. Readability changes should preserve the final HEX byte for byte when
possible. Keep upstream notices, document all borrowed code and use the existing
GPL-2.0-or-later license for contributions. Do not add a copyright holder's name
without their authorization.

Before publishing a release, complete the hardware checklist in
[docs/TESTING.md](docs/TESTING.md), or state which acceptance tests remain pending
alongside the hardware tests already completed. Publish matching sources and third-party license notices
alongside binaries. The archive does not contain a compiler toolchain.

Do not run simultaneous builds: GCC LTO writes shared temporary files. Source
license scope and redistribution requirements are documented in [LICENSES.md](LICENSES.md).
