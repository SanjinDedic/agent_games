#!/usr/bin/env bash
#
# CPU watch for the submission benchmark.
#
# The benchmark's real question is not "how fast" but "does a killed agent leak
# a runaway process?". The signature of that bug is RESIDUAL CPU: once the load
# stops, the validator should fall back to idle. If a core stays pegged at ~100%
# after traffic ends, a timed-out agent was not fully reaped.
#
# This samples `docker stats` for the validator and simulator containers and,
# when you stop it (Ctrl-C) or after --duration, prints peak CPU during the run
# and the idle CPU from the final samples, flagging anything still hot.
#
# Only works against a LOCAL docker stack (it reads docker stats on this host).
# For a remote/prod host, watch CPU there instead (top/htop/cloud metrics).
#
# Written for bash 3.2 (the macOS system bash) -- no associative arrays, no
# mapfile. Per-container samples are kept in a temp dir, one file per container.
#
# Usage (run in one terminal, then run the benchmark in another):
#
#   ./monitor_cpu.sh                       # watch until Ctrl-C
#   ./monitor_cpu.sh --duration 180        # watch ~3 min then summarize
#   INTERVAL=1 ./monitor_cpu.sh            # sample every 1s (default 2s)
#   IDLE_THRESHOLD=15 ./monitor_cpu.sh     # flag if idle CPU% stays above 15
#
# Match containers by name substring (compose default names contain these):
#   MATCH="validator simulator"  (default)
#
set -euo pipefail

INTERVAL="${INTERVAL:-2}"
IDLE_THRESHOLD="${IDLE_THRESHOLD:-25}"   # CPU% above this, while idle => leak
IDLE_SAMPLES="${IDLE_SAMPLES:-5}"        # how many trailing samples = "idle"
DURATION=0
MATCH="${MATCH:-validator simulator}"

while [ $# -gt 0 ]; do
  case "$1" in
    --duration) DURATION="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# Resolve container names by substring against the running set (deduped).
CONTAINERS=()
for pat in $MATCH; do
  while IFS= read -r n; do
    [ -n "$n" ] && CONTAINERS+=("$n")
  done < <(docker ps --format '{{.Names}}' --filter "name=${pat}")
done
if [ ${#CONTAINERS[@]} -gt 0 ]; then
  # dedupe while keeping it simple
  CONTAINERS=($(printf '%s\n' "${CONTAINERS[@]}" | awk 'NF' | sort -u))
fi
if [ ${#CONTAINERS[@]} -eq 0 ]; then
  echo "No running containers match: $MATCH" >&2
  echo "Is the app stack up? (docker compose up -d)  Containers running:" >&2
  docker ps --format '  {{.Names}}' >&2 || true
  exit 1
fi

# Temp dir: one "<safe-name>.cpu" file per container, one CPU value per line.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/cpuwatch.XXXXXX")"
safe() { printf '%s' "$1" | tr -c 'A-Za-z0-9._-' '_'; }
cleanup() { rm -rf "$WORK"; }

echo "Watching CPU% (interval ${INTERVAL}s, idle threshold ${IDLE_THRESHOLD}%):"
printf '  %s\n' "${CONTAINERS[@]}"
echo "Start the benchmark now. Ctrl-C here when it finishes to see the summary."
echo "----------------------------------------------------------------------"

summary() {
  echo ""
  echo "======================================================================"
  echo " CPU SUMMARY"
  echo "======================================================================"
  leaked=0
  for c in "${CONTAINERS[@]}"; do
    f="$WORK/$(safe "$c").cpu"
    if [ ! -s "$f" ]; then
      printf "  %-32s (no samples)\n" "$c"
      continue
    fi
    peak=$(awk 'BEGIN{m=0} {if($1>m)m=$1} END{printf "%.1f", m}' "$f")
    idle=$(tail -n "$IDLE_SAMPLES" "$f" \
           | awk '{s+=$1; n++} END{ if(n>0) printf "%.1f", s/n; else print "0" }')
    verdict="ok"
    if awk -v a="$idle" -v t="$IDLE_THRESHOLD" 'BEGIN{exit !(a>t)}'; then
      verdict="HOT -- possible leaked runaway process"
      leaked=1
    fi
    printf "  %-32s peak %6s%%   idle(last %d) %6s%%   [%s]\n" \
      "$c" "$peak" "$IDLE_SAMPLES" "$idle" "$verdict"
  done
  echo "----------------------------------------------------------------------"
  if [ "$leaked" -eq 1 ]; then
    echo " RESULT: FAIL -- a container stayed hot while idle. A timed-out agent"
    echo "         likely leaked a process. Check 'docker top <container>' for a"
    echo "         python proc still burning CPU after the load stopped."
  else
    echo " RESULT: PASS -- all containers returned to idle after the load."
  fi
  echo "======================================================================"
  cleanup
}
trap 'summary; exit 0' INT TERM

start=$(date +%s)
while true; do
  # One no-stream snapshot of all watched containers.
  while IFS="$(printf '\t')" read -r name cpu; do
    cpu="${cpu%\%}"
    [ -z "$cpu" ] && continue
    echo "$cpu" >> "$WORK/$(safe "$name").cpu"
    printf '  %-32s %6s%%\n' "$name" "$cpu"
  done < <(docker stats --no-stream --format '{{.Name}}'"$(printf '\t')"'{{.CPUPerc}}' "${CONTAINERS[@]}")

  echo "  ---"
  if [ "$DURATION" -gt 0 ]; then
    now=$(date +%s)
    if [ $((now - start)) -ge "$DURATION" ]; then
      summary
      exit 0
    fi
  fi
  sleep "$INTERVAL"
done
