# svrngs for Omarchy

What it takes to bring [svrngs](https://github.com/alexsbryan/svrngs) and
its bar plugin, [svrngs.fam](https://github.com/alexsbryan/svrngs-fam), to
Omarchy as packages: the two pacman packages as Omarchy's package
repository wants them, the setup each runs for a person, and drafts of
`omarchy install service svrngs` and its removal.

None of this is the plugin. The plugin installs and runs without it, and
lives in its own repository so that what Omarchy's plugin marketplace
reviews is only the plugin.

## Install the packages

The plugin's latest release carries both packages. Download them, check
them, install them, then start each as yourself:

```
mkdir -p ~/Downloads/svrngs && cd ~/Downloads/svrngs
U=https://github.com/alexsbryan/svrngs-fam/releases/download/v0.2.1
curl -fLO $U/SHA256SUMS -fLO $U/svrngs-bin-1.11.1-1-x86_64.pkg.tar.zst -fLO $U/svrngs-fam-0.2.1-1-any.pkg.tar.zst
sha256sum -c SHA256SUMS
sudo pacman -U svrngs-bin-1.11.1-1-x86_64.pkg.tar.zst svrngs-fam-0.2.1-1-any.pkg.tar.zst
/usr/share/svrngs/setup-user
/usr/share/svrngs-fam/setup-user
```

If you already run svrngs from its install line, setup moves that copy
aside rather than deleting it, and your groups carry on as before. These
packages don't update themselves. They aren't signed either, so pacman
installs them from files you've downloaded and checked, not straight from
a link, though the svrngs inside is checked against the svrngs release key
when they're built.

## Packages

`packaging/arch/` holds the two packages. `svrngs-bin` is svrngs's own
[`packaging/arch`](https://github.com/alexsbryan/svrngs/tree/main/packaging/arch),
copied here for each release by `bump`, given a svrngs checkout and,
if not its HEAD, the commit to copy:

```
packaging/arch/bump 1.11.1 ~/svrngs 3b9a0506
```

It writes all of `packaging/arch/svrngs-bin/`, and `SOURCE` there says
where each file came from, so change svrngs's package and bump rather than
edit the copy. On top of svrngs's files go only what Omarchy's package
repository needs: the svrngs release key as `keys/pgp/<fingerprint>.asc`,
and each file in `packaging/arch/omarchy/` in place of svrngs's, with its
sum. That's `updated-by`, the line `svrngs update` says, worded for
Omarchy.

makepkg checks each svrngs download against the svrngs release key, so
import it once with `gpg --import packaging/arch/svrngs-bin/keys/pgp/*.asc`.
Build outside this folder, so makepkg leaves nothing in it:

```
export BUILDDIR=/tmp/svrngs-build PKGDEST=/tmp/svrngs-build/out SRCDEST=/tmp/svrngs-build/src
(cd packaging/arch/svrngs-bin && makepkg -f)
(cd packaging/arch/svrngs-fam && makepkg -f)
```

The first builds `svrngs-give-bin` beside `svrngs-bin`, as svrngs's does.

`setup-svrngs` moves an install made by svrngs's install line or by Get
svrngs aside, and starts the packaged svrngs in its place. It's the
plugin's, not svrngs's, so the `svrngs-fam` package is to install it as
`/usr/share/svrngs-fam/setup-svrngs`; 0.2.1 predates it.

`omarchy/` has drafts of `omarchy install service svrngs` and its removal,
for proposing to Omarchy.

## Remove svrngs

Removing svrngs from a computer doesn't take you out of your groups;
`svrngs leave <group>` does, so run that first for each group you want to
leave. The plugin comes off with `omarchy plugin remove svrngs.fam`.

If you got svrngs with the plugin's Get svrngs or svrngs's own install line:

```
systemctl --user disable --now svrngs
rm ~/.local/bin/svrngs ~/.config/systemd/user/svrngs.service ~/.local/share/applications/svrngs.desktop
```

If you installed the packages:

```
systemctl --user disable --now svrngs
sudo pacman -R svrngs-fam svrngs-bin
```

Either way, your groups' data stays in `~/.svrngs` until you delete that
folder. The install line also added `~/.local/bin` to your PATH in
`~/.bashrc` or `~/.zshrc`; you can leave that line. If `setup-svrngs` moved
an older svrngs aside when you installed the packages, it's still there
with `.before-package` in its name.

## Tests

`tests/package_test.py` checks `setup-svrngs` and `bump` in scratch
directories, and `tests/setup_test.py` checks `setup-user`, which links the
packaged plugin and puts it in the bar once. Neither reaches this computer's
svrngs or Omarchy's shell.

MIT, © 2026 Alex Bryan, for what is written here. What `bump` copies into
`packaging/arch/svrngs-bin/` is svrngs's, under svrngs's
[AGPL-3.0](https://github.com/alexsbryan/svrngs/blob/main/LICENSE).
