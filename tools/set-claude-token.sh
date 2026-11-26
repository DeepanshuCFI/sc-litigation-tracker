#!/bin/bash
# Test a Claude subscription token from the clipboard, and only if Anthropic
# accepts it, save it as the CLAUDE_CODE_OAUTH_TOKEN secret of a GitHub repo.
# The token is never printed and never appears on a command line.
#
# ORDER MATTERS. Start this script FIRST, then copy the token. Copying the
# token first and then copying a command to run overwrites the clipboard, and
# the command text gets saved as the secret (this is what broke the Court
# Watch secret three times in November 2026).
#
# Use:
#   1. claude setup-token                (finish the browser login)
#   2. bash tools/set-claude-token.sh    (start this; it waits up to 5 minutes)
#   3. select the token and copy it. It is printed over TWO lines: select from
#      sk-ant-oat01- to the end of the second line (79 + 29 = 108 characters).
#
# Options:
#   --check-only   test the token, do not touch GitHub
#   first argument that is not an option = repo (default: the Court Watch repo)
#   WAIT_SECS=n    how long to wait for the copy (default 300)

set -u
REPO="DeepanshuCFI/sc-litigation-tracker"
CHECK_ONLY=0
for a in "$@"; do
  case "$a" in
    --check-only) CHECK_ONLY=1 ;;
    *) REPO="$a" ;;
  esac
done
WAIT_SECS="${WAIT_SECS:-300}"

# Find the claude CLI: $CLAUDE_BIN, then PATH, then an nvm install (some
# terminals do not load nvm, so `claude` is not on their PATH).
CLAUDE_BIN="${CLAUDE_BIN:-$(command -v claude || true)}"
if [ -z "$CLAUDE_BIN" ]; then
  CLAUDE_BIN="$(ls -t "$HOME"/.nvm/versions/node/*/bin/claude 2>/dev/null | head -1)"
fi
if [ -z "$CLAUDE_BIN" ] || [ ! -x "$CLAUDE_BIN" ]; then echo "claude CLI not found"; exit 2; fi
export PATH="$(dirname "$CLAUDE_BIN"):$PATH"

# TOKEN_SOURCE_CMD exists only so the script can be tested without the clipboard
read_clip() { ${TOKEN_SOURCE_CMD:-pbpaste} 2>/dev/null | tr -d '[:space:]'; }
looks_whole() { case "$1" in sk-ant-oat01-*) [ "${#1}" -ge 100 ] ;; *) return 1 ;; esac; }

TOKEN="$(read_clip)"
if ! looks_whole "$TOKEN"; then
  echo "No token on the clipboard yet. Waiting up to $WAIT_SECS seconds."
  echo "Copy it now: select from sk-ant-oat01- to the end of the SECOND line."
  waited=0
  while [ "$waited" -lt "$WAIT_SECS" ]; do
    sleep 1; waited=$((waited + 1))
    TOKEN="$(read_clip)"
    looks_whole "$TOKEN" && break
  done
fi

LEN=${#TOKEN}
if ! looks_whole "$TOKEN"; then
  echo "Gave up. The clipboard holds $LEN characters."
  case "$TOKEN" in
    sk-ant-oat01-*)
      echo "It starts with sk-ant-oat01- but is too short: only the FIRST LINE"
      echo "was copied. The token runs over two lines." ;;
    *)
      echo "It does not start with sk-ant-oat01-, so it is not the token"
      echo "(most likely the last thing copied was a command or other text)." ;;
  esac
  echo "The GitHub secret was NOT changed."
  exit 1
fi
echo "Token found on the clipboard: $LEN characters, starts with sk-ant-oat01-."

echo "Asking Anthropic whether it accepts this token (one tiny call)..."
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN
REPLY="$(printf 'Reply with exactly: ok' | CLAUDE_CODE_OAUTH_TOKEN="$TOKEN" \
  "$CLAUDE_BIN" -p --model claude-haiku-4-5-20251001 --output-format json --max-turns 1 2>&1)"

VERDICT="$(printf '%s' "$REPLY" | python3 -c '
import json, sys
raw = sys.stdin.read()
try:
    d = json.loads(raw)
except Exception:
    print("UNREADABLE: " + raw[:200].replace("\n", " ")); sys.exit()
r = str(d.get("result") or "")[:200]
print(("REFUSED: " if d.get("is_error") else "ACCEPTED: ") + r)
')"
echo "$VERDICT"

case "$VERDICT" in
  ACCEPTED*) ;;
  *) echo "The token does not work, so the GitHub secret was NOT changed."
     exit 1 ;;
esac

if [ "$CHECK_ONLY" = "1" ]; then
  echo "Check only: the token works. GitHub was not touched."
  exit 0
fi

printf '%s' "$TOKEN" | gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo "$REPO" || {
  echo "gh could not save the secret."; exit 1; }
pbcopy </dev/null
echo "Saved to $REPO and cleared from the clipboard."
echo "Now run:  gh workflow run \"Weekly refresh\" --repo $REPO"
