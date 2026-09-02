---
name: linear-project-update
description: Post a project update to the who-does-your-agent-think-you-are Linear project - the lab notebook the write-up is drafted from. Use when an eval run returns numbers, a milestone (M0-M5) closes, a headline result moves or is invalidated, or project health changes. Goes through the Linear GraphQL API, which `orca linear` cannot reach.
---

# Linear project update

The project update stream is this project's **lab notebook**: the timestamped record the
write-up is drafted from. `notes/` stays empty on purpose - numbers live here, beside the
log file that produced them.

`orca linear` owns issue-level work but has no project-level write path (`project list` is
read-only), so this one goes through GraphQL directly.

## Steps

1. **Read every number, never recall it.** Pull each figure from the `.eval` log or the
   issue comment that carries it - `inspect-skills:reading-logs` for log access. An update
   written from memory is worse than no update.
2. **Pick health**: `onTrack` | `atRisk` | `offTrack`. Go `atRisk` the moment a dated
   milestone is threatened, not once it has already slipped.
3. **Write the body** in the shape below.
4. **Post it**, and confirm `success: true` in the response.

## Body shape

```markdown
**<what changed, one line>**

**Numbers**
- <metric> = <value> - `logs/<file>.eval`

**Reads as**
<what it means for the hypothesis, 1-2 sentences>

**Not yet trusted**
- <a number still un-hand-checked, or a judge grade not yet validated>

**Next**
- <the single next action, and the issue that carries it>
```

`Not yet trusted` is what earns this over a status ping: it is the section that stops a
soft number sliding into the write-up unchallenged. When everything really is checked,
write "nothing outstanding" - leaving the heading out hides the claim.

## Post it

```bash
set -a && source .env && set +a
python3 - <<'PY'
import json, os, subprocess

body = """<body here>"""
health = "onTrack"   # onTrack | atRisk | offTrack

q = "mutation($i:ProjectUpdateCreateInput!){ projectUpdateCreate(input:$i){ success projectUpdate{ url } } }"
r = subprocess.run(["curl", "-s", "-X", "POST", "https://api.linear.app/graphql",
    "-H", "Content-Type: application/json",
    "-H", f"Authorization: {os.environ['LINEAR_API_KEY']}",
    "-d", json.dumps({"query": q, "variables": {"i": {
        "projectId": "e159a88d-c4ed-4fd3-86b7-5819eadac97d",
        "body": body, "health": health}}})],
    capture_output=True, text=True)
print(r.stdout)
PY
```

## Cadence

One update per milestone close, plus one whenever a run returns numbers that move a
headline claim. Results, not activity - a commit is not an update.
