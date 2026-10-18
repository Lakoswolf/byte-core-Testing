#!/bin/sh
# Source-only prerequisite bootstrap; package changes require terminal approval.
set -eu
BYTE_SETUP_ORIGINAL_PATH=$PATH
export BYTE_SETUP_ORIGINAL_PATH
bootstrap_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ -f "$bootstrap_dir/setup_byte_core.py" ] || { echo 'Keep this launcher beside setup_byte_core.py.' >&2; exit 3; }
need_git=false
preview=false
for arg in "$@"; do
    case "$arg" in
        --from-repo|--repository|--repository=*|--ref|--ref=*|--source-parent|--source-parent=*|--download-only) need_git=true ;;
        --plan-only|--help|-h) preview=true ;;
    esac
done
[ -f "$bootstrap_dir/../src/byte_core/cli.py" ] || need_git=true
python_ready() {
    command -v python3 >/dev/null 2>&1 &&
        python3 -c 'import sys, tomllib; sys.exit(not (sys.version_info.major == 3 and sys.version_info >= (3, 11)))' </dev/null >/dev/null 2>&1
}
git_ready() { command -v git >/dev/null 2>&1 && git --version </dev/null >/dev/null 2>&1; }
missing_python=false
missing_git=false
python_ready || missing_python=true
if "$need_git" && ! git_ready; then missing_git=true; fi
if "$missing_python" || "$missing_git"; then
    echo "Missing prerequisites: Python 3.11+/tomllib=$missing_python; Git=$missing_git (true means missing)."
    if "$preview" || [ ! -t 0 ]; then
        echo 'No packages installed in preview/help or without an interactive terminal. Install prerequisites separately or rerun interactively without --plan-only.' >&2
        exit 3
    fi
    [ "$(id -u)" -ne 0 ] || { echo 'Run as your regular user; only APT commands use sudo.' >&2; exit 3; }
    manager=
    case "$(uname -s)" in
        Darwin) command -v brew >/dev/null 2>&1 && manager=brew ;;
        Linux) command -v apt-get >/dev/null 2>&1 && manager=apt ;;
    esac
    [ -n "$manager" ] || { echo 'Automatic installation needs APT on Linux or existing Homebrew on macOS. Install Python 3.11+ (and Git for downloads) separately, then retry.' >&2; exit 3; }
    packages=
    if "$missing_python"; then
        if [ "$manager" = brew ]; then packages=python@3.13; else packages=python3; fi
    fi
    if "$missing_git"; then packages="${packages:+$packages }git"; fi
    if [ "$manager" = apt ]; then
        command -v sudo >/dev/null 2>&1 || { echo 'sudo is required for APT; ask your administrator to install the prerequisites.' >&2; exit 3; }
        echo "Proposed commands: sudo apt-get update; sudo apt-get --no-remove install $packages"
    else
        echo "Proposed command: brew install $packages (automatic update and cleanup disabled)"
    fi
    echo 'This downloads packages from your configured package sources and installs dependencies.'
    echo 'Package-manager changes can affect other software and remain if Byte setup is cancelled or fails.'
    echo 'There is no automatic uninstall or rollback. Review the package manager output; APT also requests confirmation.'
    printf 'Install these prerequisites now? [y/N]: '
    IFS= read -r approval || exit 5
    case "$approval" in y|Y|yes|YES) ;; *) echo 'Cancelled; no packages installed.'; exit 5 ;; esac
    # Only fixed package names above are split; no command or settings are evaluated.
    if [ "$manager" = apt ]; then
        sudo apt-get update || { echo 'APT update failed; setup stopped.' >&2; exit 3; }
        sudo apt-get --no-remove install $packages || { echo 'APT installation failed or cancelled; inspect package state before retrying.' >&2; exit 3; }
        # Prefer the packaged runtime over an older user PATH shim for this process.
        if "$missing_python"; then PATH="/usr/bin:$PATH"; export PATH; fi
    else
        HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 brew install $packages || { echo 'Homebrew installation failed; inspect package state before retrying.' >&2; exit 3; }
        if "$missing_python"; then
            python_prefix=$(brew --prefix python@3.13)
            PATH="$python_prefix/libexec/bin:$PATH"; export PATH
        fi
    fi
    hash -r
    python_ready || { echo 'Python 3.11+ with tomllib is still unavailable. Your package source may provide an older Python. Select a compatible python3 on PATH; setup stopped.' >&2; exit 3; }
    if "$need_git" && ! git_ready; then echo 'Git is still unavailable; setup stopped.' >&2; exit 3; fi
    echo 'Prerequisites verified. Runtime PATH selection applies to this process only; configure future terminals separately if needed.'
fi
exec python3 "$bootstrap_dir/setup_byte_core.py" "$@"
