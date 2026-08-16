#!/usr/bin/env bash
# One-time setup for WSL (Ubuntu). Run: bash setup.sh
#
# Installs the toolkit into a local venv AND puts `ff` on your PATH, so on
# draft day you can just type `ff draft ...` from any directory - no venv to
# activate, nothing to remember. Safe to re-run.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN="$HOME/.local/bin"

if ! command -v python3 >/dev/null; then
  echo "Installing python3..."
  sudo apt update && sudo apt install -y python3 python3-venv python3-pip
fi

# The venv keeps dependencies isolated and sidesteps PEP 668
# ("externally-managed-environment") on modern Ubuntu.
[ -d "$REPO/.venv" ] || python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install --quiet --upgrade pip
"$REPO/.venv/bin/pip" install --quiet -e "$REPO"

# Symlink the console script onto PATH. Its shebang points inside the venv, so
# it runs with the right interpreter WITHOUT activation. ffcli resolves its
# data directory from the module's own location, so `ff` works from anywhere.
mkdir -p "$BIN"
ln -sf "$REPO/.venv/bin/ff" "$BIN/ff"

# Ubuntu's ~/.profile only adds ~/.local/bin to PATH if the directory existed
# at login, so a fresh install often needs this nudge - once.
if ! grep -qs 'HOME/.local/bin' "$HOME/.bashrc"; then
  {
    echo ''
    echo '# added by ff2026 setup.sh'
    echo 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH" ;; esac'
  } >> "$HOME/.bashrc"
  echo "Added ~/.local/bin to PATH in ~/.bashrc"
fi

echo
if PATH="$BIN:$PATH" ff --version >/dev/null 2>&1; then
  echo "Installed: $(PATH="$BIN:$PATH" ff --version)  ->  $BIN/ff"
else
  echo "WARNING: 'ff' did not run after install. Check $BIN/ff exists."
  exit 1
fi
echo
echo "Open a NEW terminal (or run: source ~/.bashrc), then from any directory:"
echo "  ff settings"
echo "  ff sheet --slot 6"
echo "  ff draft --round 6 --gone 11 --slot 6 --window 3 --have \"QB=1,RB=2,WR=1,TE=1\""
