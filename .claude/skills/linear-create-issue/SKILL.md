---
name: linear-create-issue
description: Create a Linear issue on the who-does-your-agent-think-you-are project with complete metadata. Use when work is discovered mid-task that is out of scope, a run or review turns up a follow-up, or faiz asks for a ticket. Sets the milestone, priority and label that a bare create leaves empty - `orca linear create` has no `--milestone` flag, so this goes through the Linear GraphQL API.
---

# Create a Linear issue

`orca linear` owns issue CRUD, but every project-level field is out of its reach: it has
no `--milestone` flag, so an issue created through it is milestone-less and drops out of
the project's progress view. That is what this skill exists to close.

An issue lands complete or not at all. Title, priority and label are decided here - never
"filed now, triaged later".

## Steps

1. **Title the outcome.** See the rule below. Write this first; a title you cannot state as
   an outcome usually means you have not worked out what the ticket is for.
2. **Infer milestone, priority and label** from the tables below.
3. **Fill the "Research task" template** - fetch it rather than retyping its shape, so the
   template stays the one source of truth for how a ticket reads.
4. **Create it** with the script below, and report the identifier and URL.

## Title: outcome, not finding

Name the state you want to reach. Evidence, counts and symptoms go in the body, which is
where the reader looks once the title has earned their attention.

| Instead of | Write |
|---|---|
| `Design spec is stale: says 42 episodes / 7 scenarios, harness runs 60 / 10` | `Fix drift in the design spec` |
| `Fix gated-access exception in owned-compute handler` | `Restore access for owned-compute users` |
| `Judge returns UNKNOWN on 4% of samples` | `Make every judge grade parse` |

Roughly eight words. One clause - a colon carrying a second clause means the evidence has
crept back in.

## Milestone

**Research issues require a milestone. Tooling and workflow issues omit it.**

Board plumbing, skills and conventions sit outside the M0-M5 research arc. They carry the
`tooling` label instead, which is how they stay findable once they are off the project
progress bar.

For research work, pick the milestone whose work this issue would **corrupt or unblock**
if left undone - not the one where the problem originated, which is often already closed.

| Milestone | Covers |
|---|---|
| `M0: Harness foundation` | react harness, personas, scenarios, blind judge |
| `M1: Novelty pivot build` | proximity bundle, role-gated class, cue logging, pushback arm |
| `M2: Pilot runs` | executing the matrix, cost projections, run health |
| `M3: Analysis & validation` | deference gap, calibration split, identity-seeking, judge agreement |
| `M4: Write-up & submit` | the write-up, figures, application answers |
| `M5: Extensions` | counterfactual reveal, cue ablations, activation probes - post-application |

When research work fits none of them, say so and ask rather than defaulting to M5. A
milestone that does not exist is a finding about the plan.

## Priority (required)

| | When |
|---|---|
| `urgent` | Blocks the next dated milestone. Someone should stop what they are doing. |
| `high` | On the critical path to the next dated milestone. |
| `medium` | Wanted for the current milestone; survivable if it slips. |
| `low` | Post-deadline, or M5. |

## Label

At least one, from the vocabulary in CLAUDE.md. Two carry obligations: `spend` on anything
burning frontier tokens, so a run gets a cost projection before it starts; `tooling` on
milestone-less workflow work, so it stays findable.

## Create it

```bash
set -a && source .env && set +a
python3 - <<'PY'
import json, os, subprocess

TITLE     = "Fix drift in the design spec"
MILESTONE = "M3: Analysis & validation"   # exact name from the table, or None for tooling
PRIORITY  = "high"                        # urgent | high | medium | low
LABELS    = ["harness"]
BODY      = """<the filled-in template>"""

PROJECT = "e159a88d-c4ed-4fd3-86b7-5819eadac97d"
TEAM    = "6b255f73-8c19-474a-8155-d45e6e9f512f"
PRIO    = {"urgent": 1, "high": 2, "medium": 3, "low": 4}

def gql(query, variables=None):
    r = subprocess.run(["curl", "-s", "-X", "POST", "https://api.linear.app/graphql",
        "-H", "Content-Type: application/json",
        "-H", f"Authorization: {os.environ['LINEAR_API_KEY']}",
        "-d", json.dumps({"query": query, "variables": variables or {}})],
        capture_output=True, text=True)
    out = json.loads(r.stdout)
    if "errors" in out:
        raise SystemExit(json.dumps(out["errors"], indent=2))
    return out["data"]

# Resolve names to ids at run time so nothing here goes stale.
d = gql("""query($p:String!,$t:String!){
  project(id:$p){ projectMilestones(first:20){nodes{id name}} }
  team(id:$t){ labels(first:50){nodes{id name}} states(first:30){nodes{id name}} }
  viewer{ id }
  templates{ id name team{ id } }
}""", {"p": PROJECT, "t": TEAM})

ms   = {m["name"]: m["id"] for m in d["project"]["projectMilestones"]["nodes"]}
lbl  = {l["name"]: l["id"] for l in d["team"]["labels"]["nodes"]}
st   = {s["name"]: s["id"] for s in d["team"]["states"]["nodes"]}
tpl  = next((t["id"] for t in d["templates"]
             if t["name"] == "Research task" and t["team"] and t["team"]["id"] == TEAM), None)

missing = [l for l in LABELS if l not in lbl]
assert not missing, f"unknown labels {missing}; have {list(lbl)}"
if MILESTONE is None:
    assert "tooling" in LABELS, "a milestone-less issue must carry the `tooling` label"
else:
    assert MILESTONE in ms, f"unknown milestone {MILESTONE!r}; have {list(ms)}"

payload = {
    "teamId": TEAM, "projectId": PROJECT,
    "title": TITLE, "description": BODY,
    "priority": PRIO[PRIORITY],
    "labelIds": [lbl[l] for l in LABELS],
    "stateId": st["Backlog"],
    "assigneeId": d["viewer"]["id"],
    "lastAppliedTemplateId": tpl,
}
if MILESTONE is not None:
    payload["projectMilestoneId"] = ms[MILESTONE]

res = gql("""mutation($i:IssueCreateInput!){
  issueCreate(input:$i){ success issue{ identifier url branchName } } }""", {"i": payload})
print(json.dumps(res["issueCreate"], indent=2))
PY
```

`branchName` in the response is Linear's suggested branch name - use it, per CLAUDE.md.

## Fetching the template

Linear stores the body as a ProseMirror document under `templateData.descriptionData`, not
as markdown, so reading it back needs a render pass. `templateData.description` is empty -
Linear rewrites the field on save.

```bash
set -a && source .env && set +a
curl -s -X POST https://api.linear.app/graphql \
  -H "Content-Type: application/json" -H "Authorization: $LINEAR_API_KEY" \
  -d '{"query":"query { templates{ name templateData } }"}' | python3 -c '
import json, sys

def render(node, out):
    t = node.get("type"); kids = node.get("content", [])
    if t == "text":       out.append(node.get("text", "")); return
    if t == "hard_break": out.append("\n"); return
    if t == "heading":
        out.append("#" * node.get("attrs", {}).get("level", 2) + " ")
        for c in kids: render(c, out)
        out.append("\n\n"); return
    if t == "code_block":
        body = []
        for c in kids: render(c, body)
        out.append("```" + (node.get("attrs", {}).get("language") or "") + "\n" + "".join(body) + "\n```\n\n"); return
    if t == "todo_item":
        body = []
        for c in kids: render(c, body)
        out.append("- [" + ("x" if node.get("attrs", {}).get("done") else " ") + "] " + "".join(body).strip() + "\n"); return
    if t == "paragraph":
        for c in kids: render(c, out)
        out.append("\n\n"); return
    for c in kids: render(c, out)
    if t == "todo_list": out.append("\n")

for tpl in json.load(sys.stdin)["data"]["templates"]:
    if tpl["name"] != "Research task": continue
    out = []; render(json.loads(tpl["templateData"])["descriptionData"], out)
    print("".join(out).strip())
'
```
