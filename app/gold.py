"""Timeline-backed gold rules for the frozen uv backlog sweep.

These rules adapt the design's creation-cohort method to a stale/duplicate sweep
without changing the minimum-positive bar. Labels and events are candidate
signals only; a positive also requires the operator-adjudicated evidence cited
in the committed adjudication record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.uv_backlog import DUPLICATE_LABEL, MRE_LABEL

COHORT_AS_OF = datetime(2026, 10, 20, tzinfo=UTC)
STALE_OBSERVATION_DAYS = 180
STALE_CUTOFF = COHORT_AS_OF - timedelta(days=STALE_OBSERVATION_DAYS)
MIN_ADJUDICATED_POSITIVES = 30

TIER_A_MAINTAINERS = frozenset(
    {
        "BurntSushi",
        "charliermarsh",
        "ibraheemdev",
        "konstin",
        "woodruffw",
        "zanieb",
    }
)
TIER_B_MAINTAINERS = frozenset({"notatallshaw", "samypr100"})
# Explicitly observed triage contributors may support an explicitly worded gold
# request, but they cannot create gold by themselves.
TIER_C_CANDIDATE_ONLY = frozenset({"jtfmumm"})
BOTS = frozenset(
    {
        "astral-automations-bot[bot]",
        "coderabbitai[bot]",
        "github-actions[bot]",
        "qodo-code-review[bot]",
        "spdk-bot",
        "zaniebot",
    }
)
MAINTAINER_ASSOCIATIONS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})

# A stale sweep is about neglected work, not ordinary subscriptions, references,
# or cross-issue chatter. Only direct human actions can interrupt staleness.
SUBSTANTIVE_STALE_EVENTS = frozenset(
    {
        "commented",
        "labeled",
        "unlabeled",
        "assigned",
        "unassigned",
        "milestoned",
        "demilestoned",
        "closed",
        "reopened",
        "renamed",
    }
)


@dataclass(frozen=True)
class TimelineSignal:
    event: str
    actor: str | None = None
    actor_association: str | None = None
    created_at: str | None = None
    label_name: str | None = None


def parse_github_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp, returning None for missing/unparsable input."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def is_bot(actor: str | None) -> bool:
    return bool(actor) and (actor in BOTS or actor.endswith("[bot]"))


def is_accepted_maintainer(actor: str | None, association: str | None = None) -> bool:
    """Accepted Tier A/B humans, including association-proved maintainers."""
    if not actor or is_bot(actor):
        return False
    if actor in TIER_A_MAINTAINERS or actor in TIER_B_MAINTAINERS:
        return True
    return association in MAINTAINER_ASSOCIATIONS


def is_explicit_duplicate_signal(signal: TimelineSignal) -> bool:
    """A duplicate mark is a candidate only when it predates the freeze."""
    if signal.event != "marked_as_duplicate":
        return False
    created = parse_github_timestamp(signal.created_at)
    return created is not None and created < COHORT_AS_OF


def duplicate_candidate(labels: set[str], timeline: list[TimelineSignal]) -> bool:
    return DUPLICATE_LABEL in labels or any(
        is_explicit_duplicate_signal(signal) for signal in timeline
    )


def missing_reproduction_candidate(labels: set[str], timeline: list[TimelineSignal]) -> bool:
    """Current needs-mre labels and pre-freeze needs-mre events are candidates."""
    if MRE_LABEL in labels:
        return True
    return any(
        signal.event == "labeled"
        and signal.label_name == MRE_LABEL
        and (created := parse_github_timestamp(signal.created_at)) is not None
        and created < COHORT_AS_OF
        for signal in timeline
    )


def is_stale_interrupting_action(signal: TimelineSignal) -> bool:
    """Direct accepted-maintainer work during the observation window."""
    if signal.event not in SUBSTANTIVE_STALE_EVENTS:
        return False
    if not is_accepted_maintainer(signal.actor, signal.actor_association):
        return False
    created = parse_github_timestamp(signal.created_at)
    return created is not None and STALE_CUTOFF <= created < COHORT_AS_OF


def is_stale(created_at: str | None, timeline: list[TimelineSignal]) -> bool:
    """Old issue with no accepted-maintainer action in the observation window."""
    created = parse_github_timestamp(created_at)
    if created is None or created >= STALE_CUTOFF:
        return False
    return not any(is_stale_interrupting_action(signal) for signal in timeline)


def minimum_positive_verdict(count: int) -> str:
    """Return pass/fail under the design's unchanged minimum-positive rule."""
    return "pass" if count >= MIN_ADJUDICATED_POSITIVES else "fail"
