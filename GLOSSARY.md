# QueueSift

Semantic first-pass triage for a real GitHub Issues queue, where deterministic
metadata is preserved, model judgments propose, and humans authorise writes.

## Language

**Declared metadata**:
Issue type, packages, and structured fields the submitter supplied through the
issue template. It is input with provenance, never a model achievement.
_Avoid_: predicted labels (when referring to template-supplied values)

**Semantic proposal**:
A QueueSift suggestion about work templates cannot settle, such as a metadata
mismatch, duplicate, missing information, or misroute.
_Avoid_: auto-label, prediction (when referring to the whole proposal)

**Maintainer actual**:
The action or label state maintainers ultimately produced for an issue within
the observation window, used as noisy operational ground truth.
_Avoid_: gold label (without the adjudication rule that produced it)

**Shadow agreement**:
Agreement between shadow proposals and later maintainer actuals while
QueueSift has no effect on the queue. It is not time saved.
_Avoid_: time saved, acceptance rate (for shadow results)

**Assisted pilot**:
A period where a maintainer actually uses proposals while triaging, with
accept/edit/reject decisions and triage time recorded.
_Avoid_: shadow trial (when the maintainer is using the output)

**Creation cohort**:
A set of issues selected by creation time, with a uniform outcome-observation
window, used so evaluation preserves real class prevalence.
_Avoid_: test set (when cohort construction itself is the point)
