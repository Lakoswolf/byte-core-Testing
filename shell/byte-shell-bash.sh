# Bash-only optional presentation. Sourced by byte-shell.sh.
_byte_prompt_render() {
    _byte_helpers prompt --shell bash
}
byteprompt() {
    local color
    [ "$#" -le 1 ] || { printf '%s\n' 'usage: byteprompt on|off|status' >&2; return 2; }
    case "${1:-status}" in
        status) printf 'Byte prompt: %s\n' "${_BYTE_PROMPT:-off}";;
        on|enable)
            _byte_interactive || return
            [ "${_BYTE_PROMPT:-off}" = on ] && return 0
            color=$(_byte_value shell.prompt_color) || return
            case "$color" in none|cyan|green|yellow) ;; *) return 4;; esac
            _BYTE_SAVED_PS1=${PS1-}; _BYTE_SAVED_PS1_SET=${PS1+x}
            _BYTE_SAVED_PROMPTVARS=off
            shopt -q promptvars && _BYTE_SAVED_PROMPTVARS=on
            shopt -s promptvars
            case "$color" in
                none) PS1='$(_byte_prompt_render) ';;
                cyan) PS1='\[\033[36m\]$(_byte_prompt_render)\[\033[0m\] ';;
                green) PS1='\[\033[32m\]$(_byte_prompt_render)\[\033[0m\] ';;
                yellow) PS1='\[\033[33m\]$(_byte_prompt_render)\[\033[0m\] ';;
            esac
            _BYTE_PROMPT=on;;
        off|disable)
            if [ "${_BYTE_PROMPT:-off}" = on ]; then
                if [ "$_BYTE_SAVED_PS1_SET" = x ]; then PS1=$_BYTE_SAVED_PS1; else unset PS1; fi
                [ "$_BYTE_SAVED_PROMPTVARS" = on ] || shopt -u promptvars
            fi
            _BYTE_PROMPT=off;;
        *) printf '%s\n' 'usage: byteprompt on|off|status' >&2; return 2;;
    esac
}
_byte_bash_binding() {
    local line
    while IFS= read -r line; do
        case "$line" in "\"$1\":"*) printf '%s\n' "$line"; return;; esac
    done < <({ bind -m "$2" -p; bind -m "$2" -s; } 2>/dev/null)
}
_byte_bash_restore() {
    if [ -n "$3" ]; then bind -m "$1" "$3"; else bind -m "$1" -r "$2"; fi
}
_byte_bash_arrow_command() {
    local map bindings line
    for map in emacs-standard vi-insertion; do
        bindings=$(bind -m "$map" -X 2>/dev/null) || return 0
        while IFS= read -r line; do
            case "$line" in '"\e[A" '*|'"\e[B" '*) return 0;; esac
        done <<< "$bindings"
    done
    return 1
}
bytehistory() {
    [ "$#" -le 1 ] || { printf '%s\n' 'usage: bytehistory on|off|status' >&2; return 2; }
    case "${1:-status}" in
        status) printf 'Byte history search: %s\n' "${_BYTE_HISTORY:-off}";;
        on|enable)
            _byte_interactive || return
            [ "${_BYTE_HISTORY:-off}" = on ] && return 0
            if _byte_bash_arrow_command; then
                printf '%s\n' 'bytehistory: arrow shell-command bindings or unavailable bind -X prevent safe restoration; bindings preserved' >&2
                return 2
            fi
            _BYTE_HISTORY_E_UP=$(_byte_bash_binding '\e[A' emacs-standard)
            _BYTE_HISTORY_E_DOWN=$(_byte_bash_binding '\e[B' emacs-standard)
            _BYTE_HISTORY_V_UP=$(_byte_bash_binding '\e[A' vi-insertion)
            _BYTE_HISTORY_V_DOWN=$(_byte_bash_binding '\e[B' vi-insertion)
            bind -m emacs-standard '"\e[A": history-search-backward'
            bind -m emacs-standard '"\e[B": history-search-forward'
            bind -m vi-insertion '"\e[A": history-search-backward'
            bind -m vi-insertion '"\e[B": history-search-forward'
            _BYTE_HISTORY=on;;
        off|disable)
            if [ "${_BYTE_HISTORY:-off}" = on ]; then
                _byte_bash_restore emacs-standard '\e[A' "$_BYTE_HISTORY_E_UP"
                _byte_bash_restore emacs-standard '\e[B' "$_BYTE_HISTORY_E_DOWN"
                _byte_bash_restore vi-insertion '\e[A' "$_BYTE_HISTORY_V_UP"
                _byte_bash_restore vi-insertion '\e[B' "$_BYTE_HISTORY_V_DOWN"
            fi
            _BYTE_HISTORY=off;;
        *) printf '%s\n' 'usage: bytehistory on|off|status' >&2; return 2;;
    esac
}
