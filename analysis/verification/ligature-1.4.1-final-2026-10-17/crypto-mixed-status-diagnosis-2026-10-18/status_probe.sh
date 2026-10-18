#!/usr/bin/env bash
# Run `status --json` with a long bound and sample its process tree every 15 s.
set -u
ws=$1; out=$2; bound=${3:-1200}
cd "$ws"
start=$(date +%s)
timeout --kill-after=5s "$bound" python3 -I tools/ligature/ligature.pyz status --json >"$out/status.stdout" 2>"$out/status.stderr" &
pid=$!
while kill -0 "$pid" 2>/dev/null; do
  echo "=== t=$(( $(date +%s) - start ))s" >>"$out/ptree.log"
  ps -o pid,ppid,etime,pcpu,rss,args --forest -g "$(ps -o sid= -p $$ | tr -d ' ')" >>"$out/ptree.log" 2>&1
  sleep 15
done
wait "$pid"; rc=$?
echo "exit=$rc elapsed=$(( $(date +%s) - start ))s" >"$out/result.txt"
