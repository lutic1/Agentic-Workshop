# Usage status line

A status line that keeps model, context, cost and time in view while you work with a coding agent.

```
 Opus 5.5 (1M context) | ctx: 14% used | cost: $1.23/$500.00 | effort: medium | time: 12m34s
```

| Tool | What you get |
|---|---|
| Claude Code | The line above, from `statusline.sh`, including a running cost against a budget |
| Codex CLI | Codex's built-in footer set to model, project, branch, context, tokens and usage limits. Codex can't run a custom script, so there is no dollar figure (see [Codex](#codex-cli)) |

Quick install, from any folder:

```bash
# Claude Code
curl -fsSL https://raw.githubusercontent.com/lutic1/Agentic-Workshop/main/usage/install.sh | bash

# Codex CLI
curl -fsSL https://raw.githubusercontent.com/lutic1/Agentic-Workshop/main/usage/install.sh | bash -s codex

# Both
curl -fsSL https://raw.githubusercontent.com/lutic1/Agentic-Workshop/main/usage/install.sh | bash -s all
```

Working from a clone of this repo instead? Run `bash usage/install.sh` (add `codex` or `all` as above).

The installer backs up every file it edits as `<file>.bak.<timestamp>` and leaves the rest of your settings alone.

---

## Claude Code

### Requirements

- macOS or Linux. On Windows, use WSL or Git Bash.
- `jq`. Check with `jq --version`. If it's missing:
  - macOS: `brew install jq`
  - Ubuntu/Debian: `sudo apt install jq`
  - Windows: `winget install jqlang.jq`

### Install with the script

```bash
curl -fsSL https://raw.githubusercontent.com/lutic1/Agentic-Workshop/main/usage/install.sh | bash
```

This does three things:

1. Copies `statusline.sh` to `~/.claude/usage-statusline.sh` and makes it executable.
2. Backs up `~/.claude/settings.json`.
3. Sets `statusLine` in that file, replacing any status line you had before.

Then send any message in Claude Code. The line appears under the prompt.

### Install by hand

1. Copy the script into place:

   ```bash
   mkdir -p ~/.claude
   curl -fsSL https://raw.githubusercontent.com/lutic1/Agentic-Workshop/main/usage/statusline.sh -o ~/.claude/usage-statusline.sh
   chmod +x ~/.claude/usage-statusline.sh
   ```

2. Open `~/.claude/settings.json` and add this block at the top level. If the file doesn't exist, create it with just `{ }` around the block.

   ```json
   "statusLine": {
     "type": "command",
     "command": "~/.claude/usage-statusline.sh",
     "padding": 0
   }
   ```

3. Send a message in Claude Code.

### Check it works

Run the script with a sample payload:

```bash
echo '{"model":{"display_name":"Opus"},"context_window":{"used_percentage":25},"cost":{"total_cost_usd":0.42,"total_duration_ms":90000},"effort":{"level":"high"}}' \
  | ~/.claude/usage-statusline.sh
```

You should see `Opus | ctx: 25% used | cost: $0.42/$500.00 | effort: high | time: 1m30s` on an orange bar.

### What each field means

| Field | Source in Claude Code's payload | Notes |
|---|---|---|
| Model | `model.display_name` | |
| `ctx` | `context_window.used_percentage` | Claude Code calculates this against the model's real window (200K or 1M). Shows `—` until the first reply. |
| `cost` | `cost.total_cost_usd` | An estimate at API list prices. On a Pro or Max plan you aren't billed per token, so read it as "what this session would cost on the API." Resets on `/clear`. |
| Budget | `STATUSLINE_BUDGET_USD` | Defaults to $500. |
| `effort` | `effort.level` | Hidden for models without reasoning effort. |
| `time` | `cost.total_duration_ms` | Session run time, carried across resumes. |

### Change the budget

Put the variable in front of the command in `~/.claude/settings.json`:

```json
"command": "STATUSLINE_BUDGET_USD=200 ~/.claude/usage-statusline.sh"
```

### Uninstall

Delete the `statusLine` block from `~/.claude/settings.json`, or run `/statusline remove` inside Claude Code. Then delete `~/.claude/usage-statusline.sh`.

---

## Codex CLI

Codex doesn't support custom status line scripts. Its `[tui].status_line` setting only accepts a fixed list of built-in items, so `statusline.sh` can't run there. This setup picks the built-in items closest to the Claude Code line.

### Install with the script

```bash
curl -fsSL https://raw.githubusercontent.com/lutic1/Agentic-Workshop/main/usage/install.sh | bash -s codex
```

It adds `status_line` under `[tui]` in `~/.codex/config.toml`, or in `$CODEX_HOME/config.toml` if you set `CODEX_HOME`. If you already have a `status_line`, it leaves the file untouched and prints the line to paste yourself. Restart Codex afterwards.

### Install by hand

Open `~/.codex/config.toml` and add the block from [`codex-config.toml`](codex-config.toml):

```toml
[tui]
status_line = ["model-with-reasoning", "project-name", "git-branch", "context-used", "used-tokens", "five-hour-limit", "weekly-limit"]
```

If the file already has a `[tui]` section, put only the `status_line = ...` line inside it. A second `[tui]` heading makes the file invalid. Restart Codex.

### What each item means

| Item | Shows |
|---|---|
| `model-with-reasoning` | Model and reasoning level |
| `project-name` | Project folder |
| `git-branch` | Current branch |
| `context-used` | Percentage of the context window used |
| `used-tokens` | Tokens used this session |
| `five-hour-limit` | Usage left in your 5-hour window |
| `weekly-limit` | Usage left this week |

Items with no data yet are hidden until they have data. To reorder items, or pick from everything your Codex version offers, type `/statusline` inside Codex.

**Cost in dollars:** Codex only reports a dollar estimate (`estimated-thread-cost`) for Enterprise workspaces. If you're on one, add `"estimated-thread-cost"` to the list. For everyone else, the token count and limits are the closest equivalent.

### Uninstall

Delete the `status_line` line from `~/.codex/config.toml`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Line is blank | Run `jq --version` to check `jq` is installed, and `chmod +x ~/.claude/usage-statusline.sh` to make the script executable. Claude Code also hides status lines in folders you haven't trusted yet, so accept the trust prompt. |
| `effort` shows `{ "level": "medium" }` | You're on an older copy of the script. Rerun the installer. |
| `ctx: — used` | Normal before the first reply, and just after `/compact`. |
| Codex footer unchanged | Restart Codex. Then run `codex doctor` to confirm `config.toml` parses. |
