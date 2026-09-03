"""Local HTTP server for the AI-6 hand-labelling pass.

Serves the manifest built by scripts/ai6_sample_for_labelling.py one episode
at a time, blind to the judge's grade, and records each of faiz's grades to
a CSV as he goes (resumable -- already-labelled keys are skipped on
restart). The judge's grade is only revealed in the response AFTER a label
is submitted for that episode.

Usage:
    uv run python scripts/ai6_label_server.py \\
        --manifest docs/pilots/data/ai6-manifest.json \\
        --out docs/pilots/data/ai6-hand-labels.csv \\
        --port 8765
"""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from inspect_ai.log import read_eval_log_sample

sys.path.insert(0, "src")
from principal_eval.ai6_label_ui import PAGE  # noqa: E402
from principal_eval.ai6_labels import HandLabel, append_label, read_labels, summarize  # noqa: E402
from principal_eval.ai6_sampling import read_manifest  # noqa: E402
from principal_eval.ai6_transcript import render_transcript  # noqa: E402


class LabelState:
    def __init__(self, manifest_path: str, out_path: str):
        self.candidates = read_manifest(manifest_path)
        self.out_path = out_path
        done_keys = {l.key for l in read_labels(out_path)}
        self.queue = [c for c in self.candidates if c.key not in done_keys]
        self.n_done = len(self.candidates) - len(self.queue)

    def next_episode(self) -> dict | None:
        if not self.queue:
            return None
        c = self.queue[0]
        sample = read_eval_log_sample(c.log_path, id=c.sample_id, epoch=c.epoch)
        return {
            "key": c.key,
            "model": c.model,
            "persona": c.persona,
            "condition": c.condition,
            "scenario": c.scenario,
            "family": c.family,
            "transcript": render_transcript(sample),
            "_judge_grade": c.grade,  # stripped before the API response is sent
        }

    def submit(self, key: str, human_grade: str, fusion_tag: bool, note: str) -> dict:
        if not self.queue or self.queue[0].key != key:
            raise ValueError(f"key {key!r} is not the current episode")
        c = self.queue.pop(0)
        self.n_done += 1
        label = HandLabel(
            log_path=c.log_path, sample_id=c.sample_id, epoch=c.epoch,
            model=c.model, task=c.task, persona=c.persona, condition=c.condition,
            scenario=c.scenario, family=c.family, judge_grade=c.grade,
            human_grade=human_grade, fusion_tag=fusion_tag, note=note,
        )
        append_label(self.out_path, label)
        return {"judge_grade": c.grade, "agree": human_grade == c.grade}


def make_handler(state: LabelState):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                body = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/next":
                ep = state.next_episode()
                total = len(state.candidates)
                if ep is None:
                    self._json({"done": True, "summary": summarize(read_labels(state.out_path))})
                    return
                ep.pop("_judge_grade")
                self._json({"done": False, "index": state.n_done, "total": total, "episode": ep})
            else:
                self._json({"error": "not found"}, status=404)

        def do_POST(self):
            if self.path == "/api/submit":
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length))
                try:
                    result = state.submit(
                        data["key"], data["human_grade"], bool(data["fusion_tag"]), data.get("note", ""),
                    )
                except ValueError as e:
                    self._json({"error": str(e)}, status=409)
                    return
                self._json(result)
            else:
                self._json({"error": "not found"}, status=404)

        def log_message(self, fmt, *args):  # quieter default logging
            pass

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default="docs/pilots/data/ai6-manifest.json")
    ap.add_argument("--out", default="docs/pilots/data/ai6-hand-labels.csv")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    state = LabelState(args.manifest, args.out)
    print(f"{len(state.queue)} episodes remaining ({state.n_done} already labelled) -> {args.out}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(state))
    url = f"http://127.0.0.1:{args.port}/"
    print(f"serving {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
