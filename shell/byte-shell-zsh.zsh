# Zsh-only optional presentation. Sourced by byte-shell.sh.
_byte_highlight_styles() {
    local style
    # Presentation adapter for zsh-syntax-highlighting only. Other sourced
    # packages keep their own deployment-owned presentation settings.
    if [[ ${(t)ZSH_HIGHLIGHT_STYLES} = association* ]]; then
        if style=$(_byte_value shell.highlighting_command_style 2>/dev/null); then ZSH_HIGHLIGHT_STYLES[command]=$style; fi
        if style=$(_byte_value shell.highlighting_unknown_style 2>/dev/null); then ZSH_HIGHLIGHT_STYLES[unknown-token]=$style; fi
        if style=$(_byte_value shell.highlighting_path_style 2>/dev/null); then ZSH_HIGHLIGHT_STYLES[path]=$style; fi
    fi
    return 0
}
_byte_prompt_render() {
    _byte_helpers prompt --shell zsh
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
            _BYTE_SAVED_PROMPTSUBST=$options[promptsubst]
            _BYTE_SAVED_PROMPTPERCENT=$options[promptpercent]
            setopt promptsubst promptpercent
            case "$color" in
                none) PS1='$(_byte_prompt_render) ';;
                cyan|green|yellow) PS1="%F{$color}"'$(_byte_prompt_render)%f ';;
            esac
            _BYTE_PROMPT=on;;
        off|disable)
            if [ "${_BYTE_PROMPT:-off}" = on ]; then
                if [ "$_BYTE_SAVED_PS1_SET" = x ]; then PS1=$_BYTE_SAVED_PS1; else unset PS1; fi
                [ "$_BYTE_SAVED_PROMPTSUBST" = on ] || unsetopt promptsubst
                [ "$_BYTE_SAVED_PROMPTPERCENT" = on ] || unsetopt promptpercent
            fi
            _BYTE_PROMPT=off;;
        *) printf '%s\n' 'usage: byteprompt on|off|status' >&2; return 2;;
    esac
}
_byte_zsh_binding() {
    local -a binding
    binding=(${(z)$(bindkey -M "$1" "$2")})
    printf '%s' "${(Q)binding[2]}"
}
_byte_zsh_arrow_macro() {
    local map key binding
    for map in emacs viins; do
        for key in '^[[A' '^[[B'; do
            binding=$(bindkey -M "$map" -L "$key")
            case "$binding" in 'bindkey -s '*) return 0;; esac
        done
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
            # String macros need a different restoration grammar; refuse before changing anything.
            if _byte_zsh_arrow_macro; then
                printf '%s\n' 'bytehistory: existing arrow-key macros are preserved; remove them explicitly before enabling' >&2
                return 2
            fi
            _BYTE_HISTORY_E_UP=$(_byte_zsh_binding emacs '^[[A')
            _BYTE_HISTORY_E_DOWN=$(_byte_zsh_binding emacs '^[[B')
            _BYTE_HISTORY_V_UP=$(_byte_zsh_binding viins '^[[A')
            _BYTE_HISTORY_V_DOWN=$(_byte_zsh_binding viins '^[[B')
            bindkey -M emacs '^[[A' history-beginning-search-backward
            bindkey -M emacs '^[[B' history-beginning-search-forward
            bindkey -M viins '^[[A' history-beginning-search-backward
            bindkey -M viins '^[[B' history-beginning-search-forward
            _BYTE_HISTORY=on;;
        off|disable)
            if [ "${_BYTE_HISTORY:-off}" = on ]; then
                bindkey -M emacs '^[[A' "$_BYTE_HISTORY_E_UP"
                bindkey -M emacs '^[[B' "$_BYTE_HISTORY_E_DOWN"
                bindkey -M viins '^[[A' "$_BYTE_HISTORY_V_UP"
                bindkey -M viins '^[[B' "$_BYTE_HISTORY_V_DOWN"
            fi
            _BYTE_HISTORY=off;;
        *) printf '%s\n' 'usage: bytehistory on|off|status' >&2; return 2;;
    esac
}
