#!/usr/bin/env bash
#
# Claude Code status line: model | context used | cost vs budget | effort | time
#
# Claude Code pipes a JSON session payload to stdin on every update; this
# script prints one colored line. Requires jq.
#
# Set STATUSLINE_BUDGET_USD in the statusLine command to change the budget.

set -u
export LC_ALL=C

BUDGET_USD="${STATUSLINE_BUDGET_USD:-500}"

BG=$'\033[48;2;232;90;42m'
FG=$'\033[38;2;255;255;255m'
ACCENT=$'\033[38;2;242;160;122m'
DIM=$'\033[38;2;251;227;210m'
RESET=$'\033[0m'
SEP=$'\x1f'

fields=$(jq -r '
  def effort_level:
    (.effort // .thinking.effort) as $e
    | if ($e | type) == "object" then $e.level else $e end;

  [
    (.model.display_name // .model.id // "Claude"),
    (.context_window.used_percentage | if . == null then "" else floor end),
    (.cost.total_cost_usd // 0),
    (effort_level // ""),
    (.cost.total_duration_ms // 0 | floor)
  ]
  | map(tostring)
  | join("\u001f")
' 2>/dev/null) || fields=""

IFS="$SEP" read -r model ctx_pct cost_usd effort duration_ms <<< "$fields"

model=${model:-Claude}
ctx=${ctx_pct:+${ctx_pct}%}
ctx=${ctx:-—}
cost=$(printf '%.2f' "${cost_usd:-0}" 2>/dev/null || printf '0.00')
budget=$(printf '%.2f' "$BUDGET_USD" 2>/dev/null || printf '%s' "$BUDGET_USD")

elapsed=$(( ${duration_ms:-0} / 1000 ))
if (( elapsed < 60 )); then
  time_fmt="${elapsed}s"
elif (( elapsed < 3600 )); then
  time_fmt="$(( elapsed / 60 ))m$(( elapsed % 60 ))s"
else
  time_fmt="$(( elapsed / 3600 ))h$(( elapsed % 3600 / 60 ))m"
fi

bar="${ACCENT} | ${FG}"
segment() { printf '%s%s:%s %s' "$DIM" "$1" "$FG" "$2"; }

line="${BG}${FG} ${model}"
line+="${bar}$(segment ctx "${ctx} used")"
line+="${bar}$(segment cost "\$${cost}/\$${budget}")"
[[ -n "${effort:-}" ]] && line+="${bar}$(segment effort "$effort")"
line+="${bar}$(segment time "$time_fmt") ${RESET}"

printf '%s\n' "$line"
