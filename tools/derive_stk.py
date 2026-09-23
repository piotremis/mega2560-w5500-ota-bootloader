"""One-time extraction of Arduino's sign-on/parameter cases; provenance is retained."""

from pathlib import Path

s = Path("third_party/arduino-stk500v2/stk500boot.c").read_text()
license = s[
    : s.index(
        "//************************************************************************"
    )
]
cases = s[
    s.index("\t\t\t\tcase CMD_SIGN_ON:") : s.index(
        "\t\t\t\tcase CMD_LEAVE_PROGMODE_ISP:"
    )
]
cases = cases.replace("msgBuffer", "packet").replace("msgLength", "out")
Path("src/arduino_cases.inc").write_text(
    "/* Project adaptation modified 2026-09-18: renamed variables and formatting. */\n"
    "/* Cases from Arduino stk500boot.c; variable names and formatting adapted. GPL-2.0-or-later. */\n"
    + cases
)
Path("docs/ARDUINO-NOTICE.txt").write_text(license)
