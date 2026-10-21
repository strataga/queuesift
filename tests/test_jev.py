import pytest
from typesafe_sdk import NoulAnswer, SystemOneResponse
from typesafe_sdk._core.response_types import Usage

from app.eval_inputs import CreationTimeIssueInput
from app.jev import (
    MRE_QUESTION,
    STALE_QUESTION,
    JevBattery,
    live_runner,
    state_for_input,
)


def _item() -> CreationTimeIssueInput:
    return CreationTimeIssueInput(
        repo="astral-sh/uv",
        number=7,
        github_id=1,
        title="Title",
        body="x" * 5000,
        author="reporter",
        author_association="NONE",
        created_at="2024-02-02T18:02:57Z",
    )


def _fake_runner(state, questions, model):
    assert set(questions) == {"mre"}
    assert state["title"] == "Title"
    assert len(state["body"]) == 4000
    return SystemOneResponse(
        model="jev-test",
        usage=Usage(input_tokens=316, output_tokens=24),
        answers={"mre": NoulAnswer(noul=0.8)},
    )


def test_battery_returns_typed_decision_with_usage() -> None:
    battery = JevBattery(runner=_fake_runner, model="jev-latest")
    decision = battery.decide("mre", state_for_input(_item()), MRE_QUESTION)
    assert decision.question == "mre"
    assert decision.probability == 0.8
    assert decision.model == "jev-test"
    assert (decision.input_tokens, decision.output_tokens) == (316, 24)


def test_battery_rejects_non_noul_answers() -> None:
    def bad_runner(state, questions, model):
        return SystemOneResponse(
            model="jev-test",
            usage=Usage(input_tokens=1, output_tokens=1),
            answers={},
        )

    with pytest.raises(TypeError):
        JevBattery(runner=bad_runner).decide("stale", {}, STALE_QUESTION)


def test_live_runner_is_disabled_by_default() -> None:
    with pytest.raises(RuntimeError):
        live_runner({}, {"mre": MRE_QUESTION}, None)
