#!/bin/sh
# Optional bootstrap helpers. No profiles or deployment configuration are sourced.
_byte_prior_session=0
if [ "${_BYTE_CORE_PID:-}" = "$$" ] && command -v _byte_session_active >/dev/null 2>&1; then _byte_prior_session=1; fi
_byte_session_active() { return 0; }
_byte_cd() {
    if [ -n "${ZSH_VERSION:-}" ]; then builtin cd "$@"; else command cd "$@"; fi
}

byte_status() { printf '%s\n' 'Byte shell integration is active.'; }

byte_repo() {
    if [ "$#" -ne 1 ]; then
        printf '%s\n' 'usage: byte_repo PATH' >&2
        return 2
    fi
    if [ ! -d "$1" ] || [ "$(CDPATH= _byte_cd -- "$1" 2>/dev/null && command git rev-parse --is-inside-work-tree 2>/dev/null)" != true ]; then
        printf '%s\n' 'byte_repo: directory must be an existing Git worktree' >&2
        return 1
    fi
    CDPATH= _byte_cd -- "$1"
}

_byte_helpers() {
    if [ ! -f "${_BYTE_CORE_LAUNCHER:-}" ]; then
        printf '%s\n' 'Byte helpers require an asset beside ../bin/byte; source it in Bash or Zsh.' >&2
        return 4
    fi
    command sh "$_BYTE_CORE_LAUNCHER" helpers "$@"
}
_byte_value() { _byte_helpers config get "$1"; }

bytehelp() {
    printf '%s\n' \
        'Experimental Byte helpers (not a supported installed interface):' \
        'byte_status | byte_repo PATH | bytehelp | bytewhere | bytesafety | rebyte' \
        'dev | byten [ARGS...] | byter [ARGS...] | bytegit [STATUS_ARGS...]' \
        'byteprompt on|off|status | bytehistory on|off|status | bytehighlight on|off|status' \
        'bytealiases on|off|status (optional ll, la, ..)' \
        'labstatus | canisync | wakelan: use --help for explicit plans and approvals.' \
        'Select deployment-owned TOML with BYTE_CORE_HELPERS_CONFIG; never source it.'
}
bytewhere() {
    printf 'Shell asset: %s\nHelper launcher: %s\nConfiguration: %s\n' \
        "${_BYTE_CORE_ASSET:-unknown (POSIX shell)}" "${_BYTE_CORE_LAUNCHER:-unavailable}" \
        "${BYTE_CORE_HELPERS_CONFIG:-not selected; generic defaults only}"
    printf '%s\n' 'This is local context; do not include it in public reports.'
}
bytesafety() {
    printf '%s\n' \
        'Core owns behavior and structure; deployments own identity and truth.' \
        'Check target state, review exact scope and backout, apply only approved actions, verify results.' \
        'Configuration is data, never authorization. Network and mutation helpers require explicit scope.' \
        'Keep deployment content, logs, credentials, and observed state outside public Core history.'
}
rebyte() {
    if [ "$#" -ne 0 ] || [ ! -r "${_BYTE_CORE_ASSET:-}" ]; then
        printf '%s\n' 'rebyte: source the asset in Bash or Zsh first; no arguments accepted' >&2
        return 2
    fi
    . "$_BYTE_CORE_ASSET"
}
dev() {
    [ "$#" -eq 0 ] || { printf '%s\n' 'usage: dev' >&2; return 2; }
    _byte_dev=$(_byte_value shell.development_directory) || return
    CDPATH= _byte_cd -- "$_byte_dev"
    _byte_result=$?
    unset _byte_dev
    return "$_byte_result"
}
byten() { _byte_helpers assistant new -- "$@"; }
byter() { _byte_helpers assistant resume -- "$@"; }
bytegit() { _byte_helpers git-status -- "$@"; }
labstatus() { _byte_helpers labstatus "$@"; }
canisync() { _byte_helpers canisync "$@"; }
wakelan() { _byte_helpers wakelan "$@"; }

_byte_interactive() {
    case $- in *i*) return 0;; esac
    printf '%s\n' 'Byte presentation features require an interactive Bash or Zsh shell.' >&2
    return 2
}
bytealiases() {
    [ "$#" -le 1 ] || { printf '%s\n' 'usage: bytealiases on|off|status' >&2; return 2; }
    case "${1:-status}" in
        status) printf 'Byte aliases: %s\n' "${_BYTE_ALIASES:-off}";;
        on|enable)
            _byte_interactive || return
            if [ "${_BYTE_ALIASES:-off}" = on ]; then return 0; fi
            _BYTE_ALIAS_LL=0; _BYTE_ALIAS_LA=0; _BYTE_ALIAS_UP=0
            if ! command -v ll >/dev/null 2>&1 && ! alias ll >/dev/null 2>&1; then alias ll='ls -l'; _BYTE_ALIAS_LL=1; fi
            if ! command -v la >/dev/null 2>&1 && ! alias la >/dev/null 2>&1; then alias la='ls -A'; _BYTE_ALIAS_LA=1; fi
            if ! command -v .. >/dev/null 2>&1 && ! alias .. >/dev/null 2>&1; then alias ..='cd ..'; _BYTE_ALIAS_UP=1; fi
            _BYTE_ALIASES=on;;
        off|disable)
            # Only remove definitions still equal to the ones Byte installed.
            if [ "${_BYTE_ALIAS_LL:-0}" = 1 ] && [ "$(alias ll 2>/dev/null)" = "${_BYTE_ALIAS_LL_TEXT:-}" ]; then unalias ll; fi
            if [ "${_BYTE_ALIAS_LA:-0}" = 1 ] && [ "$(alias la 2>/dev/null)" = "${_BYTE_ALIAS_LA_TEXT:-}" ]; then unalias la; fi
            if [ "${_BYTE_ALIAS_UP:-0}" = 1 ] && [ "$(alias .. 2>/dev/null)" = "${_BYTE_ALIAS_UP_TEXT:-}" ]; then unalias ..; fi
            _BYTE_ALIASES=off;;
        *) printf '%s\n' 'usage: bytealiases on|off|status' >&2; return 2;;
    esac
    if [ "${1:-status}" = on ] || [ "${1:-status}" = enable ]; then
        _BYTE_ALIAS_LL_TEXT=$(alias ll 2>/dev/null)
        _BYTE_ALIAS_LA_TEXT=$(alias la 2>/dev/null)
        _BYTE_ALIAS_UP_TEXT=$(alias .. 2>/dev/null)
    fi
    return 0
}
byteprompt() { printf '%s\n' 'byteprompt requires Bash or Zsh' >&2; return 2; }
bytehistory() { printf '%s\n' 'bytehistory requires Bash or Zsh' >&2; return 2; }
_byte_highlight_styles() { return 0; }
bytehighlight() {
    [ "$#" -le 1 ] || { printf '%s\n' 'usage: bytehighlight on|off|status' >&2; return 2; }
    case "${1:-status}" in
        status) printf 'Byte highlighting: %s\n' "${_BYTE_HIGHLIGHT:-off}";;
        on|enable)
            _byte_interactive || return
            [ -n "${ZSH_VERSION:-}" ] || { printf '%s\n' 'bytehighlight requires Zsh' >&2; return 2; }
            [ "${_BYTE_HIGHLIGHT:-off}" = on ] && return 0
            if [ "${_BYTE_HIGHLIGHT:-off}" = partial ]; then
                printf '%s\n' 'Highlighting code partially loaded; start a fresh shell before trying again.' >&2
                return 2
            fi
            _byte_highlight=$(_byte_value shell.highlighting_file) || return
            [ -f "$_byte_highlight" ] && [ -r "$_byte_highlight" ] || { printf '%s\n' 'configured highlighting file must be readable' >&2; return 4; }
            printf '%s\n' 'Sourcing explicitly selected highlighting code; restart the shell to undo third-party changes.' >&2
            . "$_byte_highlight" || { _BYTE_HIGHLIGHT=partial; return 1; }
            _BYTE_HIGHLIGHT=on
            _byte_highlight_styles;;
        off|disable)
            if [ "${_BYTE_HIGHLIGHT:-off}" != off ]; then
                printf '%s\n' 'Third-party highlighting cannot be safely reversed. Set shell.highlighting=false and start a fresh shell.' >&2
                return 2
            fi;;
        *) printf '%s\n' 'usage: bytehighlight on|off|status' >&2; return 2;;
    esac
}

# Shell identity, not an exported loaded flag, controls per-process preferences.
_byte_fresh=0
if [ "$_byte_prior_session" != 1 ]; then
    _byte_fresh=1
    _BYTE_CORE_PID=$$
    _BYTE_PROMPT=off; _BYTE_HISTORY=off; _BYTE_ALIASES=off; _BYTE_HIGHLIGHT=off
fi
BYTE_CORE_SHELL_LOADED=1
if [ -n "${BASH_VERSION:-}" ]; then
    _BYTE_CORE_ASSET=${BASH_SOURCE:-}
elif [ -n "${ZSH_VERSION:-}" ]; then
    _BYTE_CORE_ASSET=${(%):-%x}
else
    _BYTE_CORE_ASSET=
fi
if [ -n "$_BYTE_CORE_ASSET" ]; then
    _byte_asset_dir=$(CDPATH= _byte_cd -P -- "$(dirname -- "$_BYTE_CORE_ASSET")" && pwd) || return
    _BYTE_CORE_ASSET=$_byte_asset_dir/byte-shell.sh
    _BYTE_CORE_LAUNCHER=$_byte_asset_dir/../bin/byte
    if [ -n "${BASH_VERSION:-}" ]; then
        . "$_byte_asset_dir/byte-shell-bash.sh"
    else
        . "$_byte_asset_dir/byte-shell-zsh.zsh"
    fi
fi
if [ "$_byte_fresh" = 1 ] && [ -n "${_BYTE_CORE_LAUNCHER:-}" ] && [ -n "${BYTE_CORE_HELPERS_CONFIG:-}" ]; then
    case $- in
        *i*)
            if _byte_helpers config validate >/dev/null; then
                [ "$(_byte_value shell.aliases)" != true ] || bytealiases on
                [ "$(_byte_value shell.prompt)" != true ] || byteprompt on
                [ "$(_byte_value shell.history)" != true ] || bytehistory on
                [ "$(_byte_value shell.highlighting)" != true ] || bytehighlight on
            fi;;
    esac
fi
unset _byte_asset_dir _byte_fresh _byte_prior_session
# A failed optional feature must not make sourcing the generic helpers fail.
true
