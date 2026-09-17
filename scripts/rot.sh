#!/usr/bin/env bash
#
# rot.sh — run every ticket's check block and report what has gone false.
#
# This is the whole rot detector. It has no dependencies beyond bash, awk and
# whatever the checks themselves invoke. Run it locally any time:
#
#     bash scripts/rot.sh            # all tickets
#     bash scripts/rot.sh T-0002     # one ticket
#
# Exit 1 means something claimed VERIFIED is no longer true. That is the only
# condition that fails the run, and it is deliberately loud: a rot detector
# that fails quietly is a second layer of prose claims with extra steps.

set -uo pipefail
cd "$(dirname "$0")/.."

TICKETS=docs/tickets
AREAS="digest pulse pipeline backstory editorial infra corpus process"
KINDS="defect feature chore decision"

filter="${1:-}"

# --- Is this tree even current?
# Pulse publishes through GitHub's API, so a publish lands on origin/main and
# NOT on this laptop. Every check below reads local files, so running this
# straight after a publish measures the PREVIOUS digest and reports it as
# current. That is this project's signature failure wearing a new hat --
# verifying the artifact in front of you rather than the system -- so it is
# checked first and it is fatal.
#
# Only meaningful on main: a feature branch is behind origin/main by design,
# and CI checks out the PR head. ROT_NO_FETCH=1 skips it.
if [ -z "${ROT_NO_FETCH:-}" ] && [ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" = "main" ]; then
  if git fetch -q origin main 2>/dev/null; then
    behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
    if [ "${behind:-0}" -gt 0 ]; then
      echo "STALE TREE - $behind commit(s) behind origin/main."
      echo
      echo "  Pulse publishes through GitHub, so a publish is not on this"
      echo "  laptop until you pull. Every check would measure the previous"
      echo "  digest and report it as current."
      echo
      echo "  Run:  git pull --rebase"
      exit 1
    fi
  else
    SYNC_NOTE="offline - could not confirm this tree matches origin/main"
  fi
fi
stale=0; ok=0; open=0; ready=0; manual=0; skipped=0; badmeta=0

fm() { # fm <file> <key>
  awk -v k="$2" '
    NR==1 && $0=="---" { f=1; next }
    f && $0=="---" { exit }
    f && $0 ~ "^"k":" { sub("^"k":[[:space:]]*",""); print; exit }
  ' "$1"
}

check_block() { # everything inside the first fence after "## Check"
  awk '
    /^## Check/ { c=1; next }
    c && /^```/ { if (inf) exit; inf=1; next }
    inf { print }
  ' "$1"
}

manual_note() {
  awk '/^## Check/{c=1;next} c && /^manual:/{sub("^manual:[[:space:]]*",""); print; exit}' "$1"
}

say() { printf '%-9s %-8s %s\n' "$1" "$2" "$3"; }

for f in "$TICKETS"/T-*.md; do
  [ -e "$f" ] || continue
  id=$(fm "$f" id)
  [ -n "$filter" ] && [ "$id" != "$filter" ] && continue

  title=$(fm "$f" title)
  status=$(fm "$f" status)
  anchor=$(fm "$f" anchor)
  tags=$(fm "$f" tags | tr -d '[]"' | tr ',' ' ')

  # --- metadata hygiene: the tag vocabulary is enforced, not merely documented
  base=$(basename "$f" .md)
  [ "$(echo "$base" | cut -d- -f1,2)" = "$id" ] || { say ERR "$id" "id does not match filename $base"; badmeta=1; }
  na=0; nk=0
  for t in $tags; do
    case " $AREAS " in *" $t "*) na=$((na+1));; esac
    case " $KINDS " in *" $t "*) nk=$((nk+1));; esac
  done
  if [ "$na" -ne 1 ] || [ "$nk" -ne 1 ]; then
    say ERR "$id" "tags must be exactly one area + one kind (got: $tags)"; badmeta=1
  fi

  case "$status" in
    DISCARDED|PROPOSED) say SKIP "$id" "$status — $title"; skipped=$((skipped+1)); continue;; 
  esac

  # --- anchor rot: if the code moved, the ticket needs re-reading
  if [ -n "$anchor" ]; then
    apath="${anchor%%:*}"; aline="${anchor#*:}"
    if [ ! -e "$apath" ]; then
      say ANCHOR "$id" "gone: $anchor"
      [ "$status" = VERIFIED ] && stale=$((stale+1))
      continue
    elif [ "$aline" != "$anchor" ] && [ "$(wc -l < "$apath")" -lt "$aline" ]; then
      say ANCHOR "$id" "file shorter than line $aline: $anchor"
    fi
  fi

  note=$(manual_note "$f")
  if [ -n "$note" ]; then
    say MANUAL "$id" "$note"; manual=$((manual+1)); continue
  fi

  body=$(check_block "$f")
  if [ -z "$body" ]; then
    say ERR "$id" "no check block and no manual: note"; badmeta=1; continue
  fi

  if out=$(bash -e -c "$body" 2>&1); then pass=1; else pass=0; fi

  case "$status:$pass" in
    VERIFIED:1) say OK     "$id" "$title"; ok=$((ok+1));;
    VERIFIED:0) say STALE  "$id" "$title"; stale=$((stale+1))
                [ -n "$out" ] && echo "$out" | sed 's/^/            /';;
    *:0)        say OPEN   "$id" "$title"; open=$((open+1));;
    *:1)        say READY  "$id" "$title — check passes, promote to VERIFIED"; ready=$((ready+1));;
  esac
done

echo
[ -n "${SYNC_NOTE:-}" ] && echo "note: $SYNC_NOTE"
echo "ok $ok · open $open · ready $ready · manual $manual · skipped $skipped · stale $stale"

if [ "$badmeta" -ne 0 ]; then
  echo "FAIL: ticket metadata is malformed (see ERR above)."; exit 1
fi
if [ "$stale" -ne 0 ]; then
  echo "FAIL: $stale ticket(s) claim VERIFIED but their checks no longer pass."
  echo "Fix the code, or change the status and say why. Do not edit the check to match."
  exit 1
fi
echo "No rot."
