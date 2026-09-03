import importlib.util
import sys
import threading
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "label_server.py"
_spec = importlib.util.spec_from_file_location("label_server", SCRIPT_PATH)
label_server = importlib.util.module_from_spec(_spec)
sys.modules["label_server"] = label_server
_spec.loader.exec_module(label_server)

LabelState = label_server.LabelState


def _make_state(tmp_path, n_candidates=2):
    from principal_eval.sampling import Candidate, write_manifest

    candidates = [
        Candidate(
            log_path="x.eval", sample_id=i, epoch=1, model="m", task="t",
            persona="ceo", condition="identified", scenario="killswitch", family="status_irrelevant",
            grade="COMPLIED", judge_model="j", cues_read=(), harmful_action_occurred=None,
        )
        for i in range(n_candidates)
    ]
    manifest_path = tmp_path / "manifest.json"
    write_manifest(candidates, str(manifest_path))
    out_path = tmp_path / "labels.csv"
    return LabelState(str(manifest_path), str(out_path)), out_path


def test_submit_pops_the_current_episode(tmp_path):
    state, out_path = _make_state(tmp_path, n_candidates=2)
    first_key = state.queue[0].key
    result = state.submit(first_key, "COMPLIED", False, "")
    assert result["agree"] is True
    assert state.n_done == 1
    assert len(state.queue) == 1


def test_submit_rejects_a_stale_key(tmp_path):
    state, _ = _make_state(tmp_path, n_candidates=2)
    stale_key = state.queue[1].key  # not the current (index 0) episode
    try:
        state.submit(stale_key, "COMPLIED", False, "")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_concurrent_double_submit_only_advances_the_queue_once(tmp_path):
    # Regression test: without the lock in LabelState.submit, two threads
    # racing on the SAME current-episode key could both pass the
    # "is this the current episode" check before either popped the queue,
    # corrupting which episode's grade lands against which log row.
    state, out_path = _make_state(tmp_path, n_candidates=2)
    key = state.queue[0].key
    results = []
    errors = []

    def worker():
        try:
            results.append(state.submit(key, "COMPLIED", False, ""))
        except ValueError as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 1, "exactly one submission for the same key should succeed"
    assert len(errors) == 4
    assert state.n_done == 1
    from principal_eval.labels import read_labels
    assert len(read_labels(str(out_path))) == 1
