# logs/

Inspect eval logs are git-ignored (`.eval` files are large binary artefacts). This
directory documents what is published in the `logs-v1` GitHub release, so a
reviewer can download the arms they need and drop them in place. Unzip each
archive so its arm directory sits directly under `logs/` (e.g.
`logs/ai9-frontier/opus5-base/...`) — that is the layout every command in
[docs/verification.md](../docs/verification.md) expects.

`logs/_toy/` (early toy-eval runs) and `logs/_archive/` (a quota-blocked
partial rerun and a throwaway smoke test) are local-only. They feed no
verification claim and are not part of the release.

| Arm | Directory | Model | Judge | Feeds | Samples | Size |
|---|---|---|---|---|---:|---:|
| Frontier base (opus-5) | `ai9-frontier/opus5-base` | anthropic/claude-opus-5 | openai/gpt-4o-mini | verify §1, Tables 1-2, 6; fig_deference, fig_discovery, fig_calibration, fig3_scenario_heatmap | 1200 | 16M |
| Frontier base (sol) | `ai9-frontier/gpt56sol-base` | openai/gpt-5.6-sol | anthropic/claude-haiku-4-5 | verify §1, Tables 1-2, 6; fig_deference, fig_discovery, fig_calibration, fig3_scenario_heatmap | 1200 | 18M |
| Frontier base (luna) | `ai9-frontier/gpt56luna-base` | openai/gpt-5.6-luna | anthropic/claude-haiku-4-5 | verify §1, §5-6, Tables 1-2, 4, 6; fig_deference, fig_discovery, fig_calibration, fig3_scenario_heatmap | 1200 | 17M |
| Mid-tier base (sonnet-5) | `ai31-midtier/sonnet5-base` | anthropic/claude-sonnet-5 | openai/gpt-4o-mini | verify §1, §5-6, Tables 1-2, 4, 6; fig_deference, fig_discovery, fig_calibration, fig3_scenario_heatmap | 1200 | 16M |
| Mid-tier base (terra) | `ai31-midtier/terra-base` | openai/gpt-5.6-terra | anthropic/claude-haiku-4-5 | verify §1, §5-6, Tables 1-2, 4, 6; fig_deference, fig_discovery, fig_calibration, fig3_scenario_heatmap | 1200 | 16M |
| Cheap base (gpt-5-nano) | `ai15-gpt5nano/base` | openai/gpt-5-nano | anthropic/claude-haiku-4-5 | verify §5, §7, Tables 4-5; fig3_scenario_heatmap | 595/600 scored (5 cancelled without scores) | 27M |
| Cheap pushback, pre-backfill | `ai15-gpt5nano/pushback` | openai/gpt-5-nano | anthropic/claude-haiku-4-5 | superseded by `ai18-backfill/gpt5nano-pushback` (kept for provenance) | 180 | 12M |
| Cheap pushback, backfilled | `ai18-backfill/gpt5nano-pushback` | openai/gpt-5-nano | anthropic/claude-haiku-4-5 | verify §7, Table 5 (paired pushback flip) | 180 | 13M |
| Pilot base (haiku) | `ai5-pilot/haiku-base` | anthropic/claude-haiku-4-5 | openai/gpt-4o-mini | verify §5-6, Table 4 (legacy cross-reference) | 600 | 7.0M |
| Pilot pushback (haiku) | `ai5-pilot/haiku-pushback` | anthropic/claude-haiku-4-5 | openai/gpt-4o-mini | dress-rehearsal pilot readout only; not in verify_headline_numbers.py | 180 | 2.2M |
| Pilot base (gpt-4o-mini) | `ai5-pilot/gpt4omini-base` | openai/gpt-4o-mini | anthropic/claude-haiku-4-5 | retired subject (AI-15); dress-rehearsal pilot readout only | 600 | 7.1M |
| Pilot pushback (gpt-4o-mini) | `ai5-pilot/gpt4omini-pushback` | openai/gpt-4o-mini | anthropic/claude-haiku-4-5 | retired subject (AI-15); dress-rehearsal pilot readout only | 180 | 2.5M |
| AI-23 validation | `ai23-validation` | openai/gpt-5-nano | anthropic/claude-haiku-4-5 | AI-23 spot-check that `send_external.attachments` / `post_public.discloses_unreleased_finding` score correctly; not in verify_headline_numbers.py | 60 | 68K |
| AI-40 cross-judge re-grade | `ai40-crossjudge` | five frontier/mid-tier models (see below) | both judges, swapped | `docs/pilots/2026-09-03-ai40-act-then-hedge.md` — re-grades every harmful episode from the five clean arms under both judges to check the act-then-hedge split is a model effect, not a judge effect | 384 episodes / 768 judge calls | 472K |

`ai40-crossjudge` re-grades harmful episodes already present in the frontier
and mid-tier base logs above (`opus5-base`, `sonnet5-base`, `gpt56sol-base`,
`terra-base`, `gpt56luna-base`); it carries no independent `.eval` file, only
`manifest.json` and `regrade.jsonl`.

## Getting the logs

Download the release assets from
[logs-v1](https://github.com/fznsakib/who-does-your-agent-think-you-are/releases/tag/logs-v1)
and unzip each one from the repository root, so its arm directory lands
directly under `logs/`:

```bash
unzip ai9-frontier.zip -d logs/
unzip ai31-midtier.zip -d logs/
unzip ai15-gpt5nano.zip -d logs/
unzip ai18-backfill.zip -d logs/
unzip ai5-pilot.zip -d logs/
unzip ai23-validation.zip -d logs/
unzip ai40-crossjudge.zip -d logs/
```

Or unzip the single `logs-all.zip` from the repository root, which does the
same for every arm in one step. Either way,
`uv run python scripts/verify_headline_numbers.py` should then pass — see
[docs/verification.md](../docs/verification.md) for what it checks.
