"""The stages of plan 3 end to end over the mini run, with and without annotations: fake clients only."""
import re
from pathlib import Path

from fakes import AnswerProvider, fake_sync_client, response, text, tool_use
from minirun import call_text, mini_interpretations, mini_run, summarize_answers

from scry.ask import Tools, ask
from scry.config import Config
from scry.costs import run_costs
from scry.index import build_index, open_db, search
from scry.interpret import run_interpret
from scry.run import Run
from scry.schemas import ModelInterpretation
from scry.summarize import run_summarize


def _fixture_interpretations(tmp_path: Path) -> dict[str, ModelInterpretation]:
    """Fixture M's interpretations, as what the model would have returned for each transition."""
    run = mini_run(tmp_path / "answers")
    mini_interpretations(run)
    return {i: ModelInterpretation(**r.model_dump(include=set(ModelInterpretation.model_fields)))
            for i, r in run.load_interpretations().items()}


def _pipeline(tmp_path: Path, labels: bool) -> tuple[Run, Config]:
    answers = _fixture_interpretations(tmp_path)
    run, cfg = mini_run(tmp_path / "run", labels=labels), Config()
    run_interpret(run, cfg, AnswerProvider(lambda kw: answers[re.search(r"^Transition (T\d+):", call_text(kw), re.M).group(1)]))
    run_summarize(run, cfg, AnswerProvider(summarize_answers))
    build_index(run, cfg)
    return run, cfg


def test_pipeline_end_to_end_with_annotations(tmp_path: Path):
    run, cfg = _pipeline(tmp_path, labels=True)
    db = open_db(run.index_db)
    assert search(db, '"git status"', cfg.index)[0]["node_id"] == "v:L4"  # one hit of each family ties at 2/61; lifetimes lead
    assert "v:S1" in [h["node_id"] for h in search(db, "Run git status", cfg.index)]
    items = Tools(run, cfg).get_transitions(24.0, 26.0)["transitions"]
    assert [(i["id"], i["submitted"]) for i in items] == [("T1", "no"), ("T2", "yes")]
    client = fake_sync_client([response([tool_use("u1", "search", {"query": '"git status"'})], "tool_use"),
                               response([text("They ran it at frame 12.")], "end_turn")])
    result = ask(run, cfg, "Did they run git status?", client)
    assert result.text == "They ran it at frame 12." and result.cost_usd > 0
    costs = run_costs(run.manifest_read())
    assert set(costs["stages"]) == {"interpret", "summarize"} and costs["per_frame_usd"] is None  # a hand-written run has no decode entry


def test_pipeline_end_to_end_without_annotations(tmp_path: Path):
    run, cfg = _pipeline(tmp_path, labels=False)
    stages = run.manifest_read()["stages"]
    assert stages["interpret"]["labels"] is False
    assert stages["index"]["by_level"] == {"frame": 4, "lifetime": 7, "transition": 3, "step": 2, "section": 1, "video": 1}
    db = open_db(run.index_db)
    assert search(db, "Overview", cfg.index) == []  # there is no description to find: part of what the no-annotation base prices
    assert search(db, '"On branch maln"', cfg.index)
