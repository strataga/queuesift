from fastapi.testclient import TestClient

from app.db import count_proposals, init_db, make_engine, store_proposal
from app.main import app
from app.models import IssueSnapshot
from app.template_parser import parse_template
from app.triage import propose

BUG_BODY = """### Submission checklist

- [x] This is a bug, not a usage question.
- [ ] I searched for similar issues.

### Package (Required)

- [ ] langchain
- [x] langchain-perplexity
- [ ] Other / not sure / general

### Reproduction Steps / Example Code (Python)

```python
import os
print(os.environ["EXAMPLE"])
```

### Error Message and Stack Trace (if applicable)

No exception is raised; output is missing expected sources.

### Description

The Agent API response drops metadata that the native SDK returns.
"""

SPARSE_BODY = """### Package (Required)

- [x] Other / not sure / general

### Description

It broke.
"""


def test_parser_extracts_declared_package_and_sections() -> None:
    parsed = parse_template(BUG_BODY)
    assert parsed.declared_packages == ["langchain-perplexity"]
    assert parsed.package_unsure is False
    assert parsed.checklist_total == 2 and parsed.checklist_checked == 1
    assert parsed.has_reproduction and parsed.has_error_text and parsed.has_description


def test_parser_marks_unsure_package() -> None:
    parsed = parse_template(SPARSE_BODY)
    assert parsed.declared_packages == []
    assert parsed.package_unsure is True
    assert parsed.has_reproduction is False


def _issue(body: str) -> IssueSnapshot:
    return IssueSnapshot(
        repo="langchain-ai/langchain",
        number=1,
        github_id=101,
        title="example",
        body=body,
        labels=["bug"],
        issue_type="Bug",
    )


def test_complete_bug_routes_human_in_slice0() -> None:
    proposal = propose(_issue(BUG_BODY))
    assert proposal.declared_packages == ["langchain-perplexity"]
    assert proposal.missing_fields == []
    assert proposal.route == "human"


def test_sparse_bug_flags_reproduction() -> None:
    proposal = propose(_issue(SPARSE_BODY))
    assert "reproduction" in proposal.missing_fields
    assert proposal.route == "assisted"
    assert proposal.package_unsure is True


def test_store_proposal_is_idempotent() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")
    init_db(engine)
    issue = _issue(BUG_BODY)
    proposal = propose(issue)
    store_proposal(engine, issue, proposal)
    store_proposal(engine, issue, proposal)
    assert count_proposals(engine) == 1


def test_healthz() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "queuesift"}
