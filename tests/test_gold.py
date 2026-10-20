from app.gold import (
    TimelineSignal,
    duplicate_candidate,
    is_accepted_maintainer,
    is_stale,
    minimum_positive_verdict,
    missing_reproduction_candidate,
)


def test_duplicate_candidate_accepts_current_label_or_prefreeze_mark() -> None:
    mark = TimelineSignal(
        event="marked_as_duplicate",
        actor="konstin",
        created_at="2025-12-18T15:20:30Z",
    )
    assert duplicate_candidate({"bug"}, [mark]) is True
    assert duplicate_candidate({"duplicate"}, []) is True
    late = TimelineSignal(
        event="marked_as_duplicate",
        actor="konstin",
        created_at="2026-10-20T00:00:01Z",
    )
    assert duplicate_candidate({"bug"}, [late]) is False


def test_missing_reproduction_candidate_accepts_prefreeze_label_signal() -> None:
    signal = TimelineSignal(
        event="labeled",
        actor="zanieb",
        created_at="2025-08-01T16:56:55Z",
        label_name="needs-mre",
    )
    assert missing_reproduction_candidate({"bug"}, [signal]) is True
    assert missing_reproduction_candidate({"needs-mre"}, []) is True
    assert missing_reproduction_candidate({"bug"}, []) is False


def test_stale_requires_old_issue_and_no_maintainer_action_in_window() -> None:
    maintainer_comment = TimelineSignal(
        event="commented",
        actor="konstin",
        actor_association="MEMBER",
        created_at="2026-08-05T09:54:40Z",
    )
    assert is_stale("2024-02-02T18:02:57Z", []) is True
    assert is_stale("2024-02-02T18:02:57Z", [maintainer_comment]) is False
    # Created inside the 180-day observation window, even with no action.
    assert is_stale("2026-09-01T00:00:00Z", []) is False
    # Bot or unknown-actor activity does not interrupt staleness.
    bot_comment = TimelineSignal(
        event="commented", actor="zaniebot", created_at="2026-08-05T16:12:13Z"
    )
    assert is_stale("2024-02-02T18:02:57Z", [bot_comment]) is True


def test_minimum_positive_verdict_uses_thirty() -> None:
    assert minimum_positive_verdict(29) == "fail"
    assert minimum_positive_verdict(30) == "pass"


def test_public_org_maintainer_counts_without_timeline_association() -> None:
    assert is_accepted_maintainer("zsol", None) is True
