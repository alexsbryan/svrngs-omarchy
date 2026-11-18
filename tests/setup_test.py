#!/usr/bin/python3 -I
"""setup-user in a scratch home, with Omarchy's shell stood in for: the
plugin is linked, placed in the bar once, and never moved again after."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures = []


def check(name, got, want):
    print(f"  {'ok  ' if got == want else 'FAIL'} {name}" + ("" if got == want else f": got {got!r}, wanted {want!r}"))
    if got != want:
        failures.append(name)


def setup(home, shell_up=True):
    stubs = home / "stubs"
    stubs.mkdir(exist_ok=True)
    answer = 'echo ok' if shell_up else 'exit 1'
    (stubs / "omarchy-shell").write_text(
        f'#!/bin/bash\nprintf "%s\\n" "$*" >> "$HOME/shell-calls"\n[[ $1 == -q ]] && exit 0\n{answer}\n')
    (stubs / "omarchy-shell").chmod(0o755)
    env = {"HOME": str(home), "PATH": f"{stubs}:/usr/bin:/bin", "SVRNGS_FAM_DIR": str(ROOT)}
    done = subprocess.run(["bash", str(ROOT / "packaging/arch/svrngs-fam/setup-user")], env=env, capture_output=True, text=True, timeout=30)
    calls = (home / "shell-calls").read_text().splitlines() if (home / "shell-calls").exists() else []
    (home / "shell-calls").unlink(missing_ok=True)
    return done, calls


with tempfile.TemporaryDirectory() as scratch:
    home = Path(scratch) / "home"
    home.mkdir()
    link = home / ".config/omarchy/plugins/svrngs.fam"

    print("first install")
    done, calls = setup(home)
    check("succeeds", done.returncode, 0)
    check("links the plugin", os.readlink(link), str(ROOT))
    check("puts it in the bar's right section", calls, ["-q shell rescanPlugins", 'shell putBarWidget svrngs.fam {"section":"right"}'])

    print("run again, after the person moved it")
    done, calls = setup(home)
    check("never places it again", calls, ["-q shell rescanPlugins"])

    print("first install while Omarchy's shell is down")
    home2 = Path(scratch) / "home2"
    home2.mkdir()
    done, calls = setup(home2, shell_up=False)
    check("still succeeds", done.returncode, 0)
    check("says it will place it later", "next time" in done.stderr, True)
    done, calls = setup(home2)
    check("and does, the next time", calls[-1], 'shell putBarWidget svrngs.fam {"section":"right"}')

print("ALL OK" if not failures else f"{len(failures)} FAILED")
sys.exit(1 if failures else 0)
