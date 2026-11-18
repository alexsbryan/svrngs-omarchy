#!/usr/bin/python3 -I
"""setup-svrngs and packaging/arch/bump, in scratch directories.

setup-svrngs moves an install made by svrngs's own install line aside, never
deleting it and never touching ~/.svrngs, and starts the packaged service;
systemctl is stood in for, so nothing reaches this computer's own svrngs.
bump copies svrngs-bin from a scratch svrngs's packaging/arch, swapping in
only omarchy/'s files and their sums, and refuses a commit it couldn't
copy honestly.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETUP = ROOT / "packaging/arch/svrngs-fam/setup-svrngs"
failures = []


def check(name, got, want):
    print(f"  {'ok  ' if got == want else 'FAIL'} {name}" + ("" if got == want else f": got {got!r}, wanted {want!r}"))
    if got != want:
        failures.append(name)


def setup(home, starts=True):
    stubs = home / "stubs"
    stubs.mkdir(exist_ok=True)
    active = "exit 0" if starts else "exit 3"
    (stubs / "systemctl").write_text(
        f'#!/bin/bash\nprintf "%s\\n" "$*" >> "$HOME/systemctl-calls"\n[[ $* == *is-active* ]] && {active}\nexit 0\n')
    (stubs / "systemctl").chmod(0o755)
    (stubs / "sleep").write_text("#!/bin/bash\nexit 0\n")
    (stubs / "sleep").chmod(0o755)
    done = subprocess.run(["bash", str(SETUP)], env={"HOME": str(home), "PATH": f"{stubs}:/usr/bin:/bin"},
                          capture_output=True, text=True, timeout=30)
    calls_file = home / "systemctl-calls"
    calls = calls_file.read_text().splitlines() if calls_file.exists() else []
    calls_file.unlink(missing_ok=True)
    return done, [c for c in calls if "is-active" not in c]


def aside(folder, name):
    return sorted(p.name for p in folder.glob(f"{name}.before-package.*"))


with tempfile.TemporaryDirectory() as scratch:
    print("an install made by svrngs's own install line")
    home = Path(scratch) / "home"
    units = home / ".config/systemd/user"
    units.mkdir(parents=True)
    (units / "svrngs.service").write_text(f"[Service]\nExecStart={home}/.local/bin/svrngs\n")
    (home / ".local/bin").mkdir(parents=True)
    (home / ".local/bin/svrngs").write_bytes(b"the svrngs the install line put here")
    (home / ".svrngs/lends").mkdir(parents=True)
    (home / ".svrngs/lends/garden.json").write_text('{"port": 3000}')
    (home / ".svrngs/token").write_text("a-token")
    before = {p.relative_to(home): p.read_bytes() for p in (home / ".svrngs").rglob("*") if p.is_file()}

    done, calls = setup(home)
    check("succeeds", done.returncode, 0)
    check("its service is stopped first", calls[0], "--user disable --now svrngs.service")
    check("its service is moved aside, not deleted", len(aside(units, "svrngs.service")), 1)
    check("so the packaged service is the one systemd finds", (units / "svrngs.service").exists(), False)
    check("its binary is moved aside, not deleted", len(aside(home / ".local/bin", "svrngs")), 1)
    kept = next((home / ".local/bin").glob("svrngs.before-package.*"))
    check("with its bytes", kept.read_bytes(), b"the svrngs the install line put here")
    check("and its name now runs the package's", os.readlink(home / ".local/bin/svrngs"), "/usr/bin/svrngs")
    check("the packaged service is started", calls[-2:], ["--user daemon-reload", "--user enable --now svrngs.service"])
    after = {p.relative_to(home): p.read_bytes() for p in (home / ".svrngs").rglob("*") if p.is_file()}
    check("~/.svrngs is untouched", after, before)

    print("run again")
    done, calls = setup(home)
    check("succeeds", done.returncode, 0)
    check("moves nothing more", (len(aside(units, "svrngs.service")), len(aside(home / ".local/bin", "svrngs"))), (1, 1))
    check("stops nothing", calls, ["--user daemon-reload", "--user enable --now svrngs.service"])

    print("a computer svrngs was never on")
    fresh = Path(scratch) / "fresh"
    fresh.mkdir()
    done, calls = setup(fresh)
    check("succeeds", done.returncode, 0)
    check("the name svrngs runs the package's", os.readlink(fresh / ".local/bin/svrngs"), "/usr/bin/svrngs")
    check("only starts the service", calls, ["--user daemon-reload", "--user enable --now svrngs.service"])

    print("a service that does not start")
    stuck = Path(scratch) / "stuck"
    stuck.mkdir()
    done, _ = setup(stuck, starts=False)
    check("fails", done.returncode, 1)
    check("and says where to look", "systemctl --user status svrngs" in done.stderr, True)

    print("bump")
    svrngs, arch = Path(scratch) / "svrngs", Path(scratch) / "svrngs/packaging/arch"
    arch.mkdir(parents=True)
    # Only this scratch config, so no one's hooks or signing reach these commits.
    quiet = {"PATH": "/usr/bin:/bin", "HOME": scratch, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
             "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

    def git(*args):
        return subprocess.run(["git", "-C", str(svrngs), *args], env=quiet, check=True, capture_output=True, text=True).stdout.strip()

    def sha(data):
        return hashlib.sha256(data).hexdigest()

    def bump(*args):
        return subprocess.run([str(fam / "bump"), *args, str(svrngs)], env=quiet, capture_output=True, text=True)

    def tree(folder):
        return {p.relative_to(folder): p.read_bytes() for p in folder.rglob("*") if p.is_file()}

    theirs = {"updated-by": b"pacman installed this svrngs\n", "svrngs.service": b"[Service]\nExecStart=/usr/bin/svrngs\n",
              "svrngs-bin.install": b"post_install() { :; }\n", "README.md": b"# Building it in svrngs\n"}
    for name, data in theirs.items():
        (arch / name).write_bytes(data)
    fpr = "46B4D67C5E6621093BB1AB2B057BF9082AA03CFB"
    pkgbuild = (f"pkgbase=svrngs-bin\npkgver=1.12.0\npkgrel=1\nvalidpgpkeys=('{fpr}')\nsource=(updated-by svrngs.service)\n"
                f"sha256sums=('{sha(theirs['updated-by'])}'\n            '{sha(theirs['svrngs.service'])}')\n"
                f"sha256sums_x86_64=('{'1' * 64}' '{'2' * 64}')\n")
    (arch / "PKGBUILD").write_text(pkgbuild)
    (svrngs / "svrngs-release-key.asc").write_bytes(b"the svrngs release key")
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-qm", "packaging/arch")
    git("init", "-q", "--bare", str(Path(scratch) / "svrngs.git"))
    git("remote", "add", "origin", str(Path(scratch) / "svrngs.git"))
    git("push", "-q", "origin", "main")
    git("fetch", "-q", "origin")
    commit = git("rev-parse", "HEAD")

    fam = Path(scratch) / "fam"
    shutil.copytree(ROOT / "packaging/arch", fam)
    out = fam / "svrngs-bin"
    (out / "setup-user").write_text("left by an older svrngs-bin\n")
    ours = (fam / "omarchy/updated-by").read_bytes()
    done = bump("1.12.0")
    check("succeeds", done.returncode, 0)
    check("a file the PKGBUILD pins is svrngs's, byte for byte", (out / "svrngs.service").read_bytes(), theirs["svrngs.service"])
    check("one it doesn't pin says where it came from",
          (out / "svrngs-bin.install").read_bytes(),
          f"# Copied by ../bump from svrngs packaging/arch/svrngs-bin.install@{commit}.\n".encode() + theirs["svrngs-bin.install"])
    check("omarchy/updated-by in place of svrngs's", (out / "updated-by").read_bytes(), ours)
    check("the PKGBUILD is svrngs's, but for updated-by's sum",
          (out / "PKGBUILD").read_text(),
          f"# Copied by ../bump from svrngs packaging/arch/PKGBUILD@{commit}, with omarchy/updated-by's sum.\n"
          + pkgbuild.replace(sha(theirs["updated-by"]), sha(ours)))
    check("the release key, where Omarchy's repository reads it", (out / f"keys/pgp/{fpr}.asc").read_bytes(), b"the svrngs release key")
    check("svrngs's README stays in svrngs", (out / "README.md").exists(), False)
    check("nothing an older copy left", (out / "setup-user").exists(), False)
    check("SOURCE names every file's origin",
          sorted(line.split("\t")[0] for line in (out / "SOURCE").read_text().splitlines() if not line.startswith("#")),
          sorted(["PKGBUILD", "svrngs.service", "svrngs-bin.install", "updated-by", f"keys/pgp/{fpr}.asc"]))

    copied = tree(out)
    done = bump("1.13.0")
    check("another version is refused", done.returncode != 0 and "pkgver=1.12.0, not 1.13.0" in done.stderr, True)
    check("and nothing changed", tree(out), copied)
    (arch / "PKGBUILD").write_text(pkgbuild.replace(f"'{sha(theirs['updated-by'])}'\n            ", ""))
    git("commit", "-qam", "updated-by, no longer pinned")
    git("push", "-q", "origin", "main")
    git("fetch", "-q", "origin")
    done = bump("1.12.0")
    check("a swap for a file svrngs doesn't pin is refused", done.returncode != 0 and "pins no updated-by" in done.stderr, True)
    check("and nothing changed", tree(out), copied)
    (arch / "PKGBUILD").write_text(pkgbuild)
    git("commit", "-qam", "not pushed")
    done = bump("1.12.0")
    check("a commit on no pushed branch is refused", done.returncode != 0 and "no pushed branch" in done.stderr, True)
    check("and nothing changed", tree(out), copied)

print("ALL OK" if not failures else f"{len(failures)} FAILED")
sys.exit(1 if failures else 0)
