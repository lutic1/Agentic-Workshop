#!/usr/bin/env bash
#
# Installs the usage status line.
#
#   install.sh           Claude Code (default)
#   install.sh codex     Codex CLI
#   install.sh all       both
#
# Works from a clone or piped from curl. Every config file it edits is backed
# up first as <file>.bak.<timestamp>.

set -euo pipefail

RAW_URL="https://raw.githubusercontent.com/lutic1/Agentic-Workshop/main/usage"
STAMP=$(date +%Y%m%d%H%M%S)

CODEX_ITEMS='["model-with-reasoning", "project-name", "git-branch", "context-used", "used-tokens", "five-hour-limit", "weekly-limit"]'

info() { printf '  %s\n' "$*"; }
fail() { printf 'error: %s\n' "$*" >&2; exit 1; }

script_dir() {
  local src="${BASH_SOURCE[0]:-}"
  [[ -n "$src" && -f "$src" ]] && cd "$(dirname "$src")" && pwd
}

fetch_statusline() {
  local dest="$1" dir
  dir=$(script_dir || true)
  if [[ -n "$dir" && -f "$dir/statusline.sh" ]]; then
    cp "$dir/statusline.sh" "$dest"
  else
    command -v curl >/dev/null || fail "curl is required to download statusline.sh"
    curl -fsSL "$RAW_URL/statusline.sh" -o "$dest"
  fi
  chmod +x "$dest"
}

install_claude() {
  echo "Claude Code"
  command -v jq >/dev/null || fail "jq is required. Install it first: brew install jq (macOS) or sudo apt install jq (Linux)."

  local claude_dir="$HOME/.claude"
  local settings="$claude_dir/settings.json"
  local script_path="$claude_dir/usage-statusline.sh"
  # Stored literally; Claude Code expands ~ when it runs the command.
  # shellcheck disable=SC2088
  local command="~/.claude/usage-statusline.sh"

  if [[ -s "$settings" ]]; then
    jq empty "$settings" 2>/dev/null || fail "$settings is not valid JSON; fix it and rerun."
  fi

  mkdir -p "$claude_dir"
  fetch_statusline "$script_path"
  info "script   $script_path"

  if [[ -s "$settings" ]]; then
    cp "$settings" "$settings.bak.$STAMP"
    info "backup   $settings.bak.$STAMP"
    local existing
    existing=$(jq -r '.statusLine.command // empty' "$settings")
    [[ -n "$existing" && "$existing" != "$command" ]] && info "replaced previous statusLine: $existing"
  else
    echo '{}' > "$settings"
  fi

  local tmp
  tmp=$(mktemp)
  jq --arg cmd "$command" '.statusLine = {type: "command", command: $cmd, padding: 0}' "$settings" > "$tmp"
  cat "$tmp" > "$settings"
  rm -f "$tmp"
  info "settings $settings"
  info "done. Send a message in Claude Code to see it."
}

install_codex() {
  echo "Codex CLI"
  local codex_dir="${CODEX_HOME:-$HOME/.codex}"
  local config="$codex_dir/config.toml"
  local line="status_line = $CODEX_ITEMS"

  mkdir -p "$codex_dir"
  touch "$config"

  if grep -Eq '^[[:space:]]*(tui\.)?status_line[[:space:]]*=' "$config"; then
    info "$config already sets status_line; left unchanged."
    info "Replace it with this line under [tui] to use this layout:"
    info "$line"
    return
  fi

  if [[ -s "$config" ]]; then
    cp "$config" "$config.bak.$STAMP"
    info "backup   $config.bak.$STAMP"
  fi

  local tmp
  tmp=$(mktemp)
  if grep -Eq '^[[:space:]]*\[tui\][[:space:]]*$' "$config"; then
    awk -v add="$line" '{ print } /^[[:space:]]*\[tui\][[:space:]]*$/ && !done { print add; done = 1 }' "$config" > "$tmp"
  else
    { cat "$config"; [[ -s "$config" ]] && echo; echo "[tui]"; echo "$line"; } > "$tmp"
  fi
  cat "$tmp" > "$config"
  rm -f "$tmp"
  info "config   $config"
  info "done. Restart Codex to see it."
}

case "${1:-claude}" in
  claude) install_claude ;;
  codex)  install_codex ;;
  all)    install_claude; echo; install_codex ;;
  *)      fail "unknown target '$1' (use claude, codex or all)" ;;
esac
