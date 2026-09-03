"""How much OpenAI daily request budget is actually left?

Reads the rate-limit HEADERS rather than just asking "did one request succeed".
That distinction matters: a single successful call only proves >=1 request was
available. During the AI-5 re-run a bare success probe gave a false green light,
the run consumed the small remaining headroom in minutes, and the whole arm then
stalled on `x-ratelimit-remaining-requests: 0` with a 24h reset.

Pass --need N to require at least N remaining requests (exit 1 if short), so a
launcher can gate a run on having enough budget to finish it.

Exit codes: 0 = enough budget, 1 = not enough / exhausted, 2 = probe failed.

Usage:
    uv run python scripts/ai5_quota_probe.py            # just report
    uv run python scripts/ai5_quota_probe.py --need 3000
"""
from __future__ import annotations

import os
import sys

import httpx

API = "https://api.openai.com/v1/chat/completions"
MODEL = "gpt-4o-mini"


def load_key() -> str | None:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env):
        for line in open(env):
            line = line.strip()
            if line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1]
    return None


def main() -> None:
    need = 0
    if "--need" in sys.argv:
        need = int(sys.argv[sys.argv.index("--need") + 1])

    key = load_key()
    if not key:
        print("PROBE_FAILED: no OPENAI_API_KEY")
        sys.exit(2)

    try:
        r = httpx.post(
            API,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": MODEL, "max_tokens": 1,
                  "messages": [{"role": "user", "content": "hi"}]},
            timeout=30,
        )
    except Exception as e:  # noqa: BLE001
        print(f"PROBE_FAILED: {e}")
        sys.exit(2)

    h = r.headers
    remaining = h.get("x-ratelimit-remaining-requests")
    limit = h.get("x-ratelimit-limit-requests")
    reset = h.get("x-ratelimit-reset-requests")
    rem_tok = h.get("x-ratelimit-remaining-tokens")
    reset_tok = h.get("x-ratelimit-reset-tokens")

    print(f"status={r.status_code} requests {remaining}/{limit} remaining, "
          f"resets in {reset}; tokens {rem_tok} remaining, resets in {reset_tok}")

    if remaining is None:
        print("PROBE_FAILED: no rate-limit headers returned")
        sys.exit(2)

    rem = int(remaining)
    if rem == 0:
        print(f"QUOTA_EXHAUSTED - 0 requests left, resets in {reset}")
        sys.exit(1)
    if need and rem < need:
        print(f"QUOTA_INSUFFICIENT - {rem} left, need {need} (resets in {reset})")
        sys.exit(1)
    print(f"QUOTA_OK - {rem} requests available")
    sys.exit(0)


if __name__ == "__main__":
    main()
