"""TypeSafe Jev battery adapter for qualified Slice 2 decisions.

Live Jev calls are disabled by default: paid provider scoring remains blocked
until measured unit pricing and a recorded nonzero spend cap exist. Tests and
offline scaffolding inject a fake runner; nothing in this module performs
network I/O by itself.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel, Field
from typesafe_sdk import Noul, NoulAnswer, SystemOneResponse

from app.eval_inputs import CreationTimeIssueInput

LIVE_JEV_ENABLED = False
MAX_STATE_CHARS = 4000

STALE_QUESTION = Noul(
    instructions=(
        "Given only the GitHub issue creation title, body, author association, "
        "and creation date in state, estimate the probability that this issue "
        "receives no accepted-maintainer action for at least 180 days. Do not "
        "use any information dated after the issue creation date."
    ),
    criteria={
        "true": "The issue remains without accepted-maintainer action for 180 days.",
        "false": "An accepted maintainer acts on the issue within 180 days.",
    },
)
MRE_QUESTION = Noul(
    instructions=(
        "Given only the GitHub issue creation title, body, author association, "
        "and creation date in state, estimate the probability that maintainer "
        "triage of this bug-like report needs more evidence: a reproduction, "
        "log, environment detail, configuration, setup steps, or another "
        "missing diagnostic artifact."
    ),
    criteria={
        "true": "The report is missing reproduction or diagnostic evidence.",
        "false": "The report already includes usable reproduction evidence.",
    },
)


class JevDecision(BaseModel):
    """A single typed battery answer with provenance for cost accounting."""

    question: str
    probability: float = Field(ge=0.0, le=1.0)
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


BatteryRunner = Callable[
    [dict, Mapping[str, Noul], str | None], SystemOneResponse
]


def state_for_input(item: CreationTimeIssueInput) -> dict:
    """Build the Jev state from creation-time fields only."""
    return {
        "title": item.title,
        "body": item.body[:MAX_STATE_CHARS],
        "author_association": item.author_association,
        "created_at": item.created_at,
    }


def live_runner(
    state: dict, questions: Mapping[str, Noul], model: str | None
) -> SystemOneResponse:
    """Constructing a live call requires explicitly enabling it first."""
    if not LIVE_JEV_ENABLED:
        raise RuntimeError(
            "live Jev calls are disabled: paid provider scoring requires "
            "measured unit pricing and a recorded nonzero spend cap"
        )
    raise NotImplementedError("live runner is not wired in this change")


@dataclass
class JevBattery:
    """Run fixed Noul questions through an injected runner."""

    runner: BatteryRunner
    model: str | None = None

    def decide(
        self, question_name: str, state: dict, question: Noul
    ) -> JevDecision:
        response = self.runner(state, {question_name: question}, self.model)
        answer = response.answers.get(question_name)
        if not isinstance(answer, NoulAnswer):
            raise TypeError(
                f"expected a Noul answer for {question_name!r}, "
                f"got {type(answer).__name__}"
            )
        return JevDecision(
            question=question_name,
            probability=answer.noul,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
