#!/bin/zsh
# AI-5 follow-up: re-run the two gpt-4o-mini arms under the AI-11 cross-provider judge.
#
# Why both: a pushback flip rate is a PAIRED grade comparison against its base arm, so
# base and pushback must share a judge. AI-11 changes the judge only for openai models
# under test, so the haiku arms (runs 1 and 3) stay valid and are NOT re-run.
#
# Run 2: principal_eval        @ gpt-4o-mini, epochs 10 -> 600 samples
# Run 4: principal_eval_pushback @ gpt-4o-mini, epochs 5 -> 180 samples
#
# Concurrency is capped deliberately. The AI-5 pilot exhausted the OpenAI 10,000
# requests-per-DAY quota because retries count against it; an uncapped adaptive ramp
# overshoots the per-minute cap, and the resulting retry storm burns the daily budget.
set -u
cd /Users/faizaan/Documents/who-does-your-agent-think-you-are

CONC=12  # tuned during AI-5: 20 overshoots, 6 underuses
STAMP=$(date +%Y%m%d-%H%M)

echo "[$(date +%H:%M:%S)] quota probe"
# Gate on ACTUAL remaining headroom, not "did one request succeed". Run 2 + run 4
# need ~2,900 successful requests plus retry headroom.
uv run python scripts/ai5_quota_probe.py --need 4000 || { echo "ABORT: insufficient OpenAI daily request budget"; exit 1; }

wait_for_idle () {
  while true; do
    n=$(uv run inspect ctl task list --json 2>/dev/null | python3 -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(1); raise SystemExit
print(len([t for t in d.get('tasks',[]) if t.get('completed_at') is None]))
" 2>/dev/null)
    [ "$n" = "0" ] && break
    sleep 20
  done
}

echo "[$(date +%H:%M:%S)] RUN 2: principal_eval @ gpt-4o-mini epochs 10 (conc $CONC)"
uv run inspect eval-set src/principal_eval/real_eval.py@principal_eval \
  --model openai/gpt-4o-mini --epochs 10 --max-connections $CONC \
  --log-dir logs/ai5-rerun/gpt4omini-base --display none \
  > /tmp/ai5-rerun-base.out 2>&1
echo "[$(date +%H:%M:%S)] run 2 exited rc=$?"

wait_for_idle

echo "[$(date +%H:%M:%S)] RUN 4: principal_eval_pushback @ gpt-4o-mini epochs 5 (conc $CONC)"
uv run inspect eval-set src/principal_eval/real_eval.py@principal_eval_pushback \
  --model openai/gpt-4o-mini --epochs 5 --max-connections $CONC \
  --log-dir logs/ai5-rerun/gpt4omini-pushback --display none \
  > /tmp/ai5-rerun-pushback.out 2>&1
echo "[$(date +%H:%M:%S)] run 4 exited rc=$?"

echo "AI5_RERUN_COMPLETE"
