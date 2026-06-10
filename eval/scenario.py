"""Shared multi-session scenario data for the demo and eval."""

from datetime import datetime, timezone, timedelta


def _future(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%dT23:59:00+00:00")


# Session 1: the team reads the contest rules and jots an (outdated) assumption.
SESSION1_RULES = (
    "Global AI Hackathon Series with Qwen Cloud — MemoryAgent track. "
    f"The final submission deadline is {_future(30)} on Devpost. "
    "Teams may have at most 4 members and must register before kickoff. "
    "Submissions must use a Qwen model via Qwen Cloud MaaS. "
    "We should still use Python 2 for the build scripts since that is what the old runner expected. "
    "The grand prize is 10000 USD."
)

# Session 2 (after a restart): a correction arrives — Python 3.11 is now required.
SESSION2_UPDATE = (
    "Update from the organizers: the runner was upgraded, so the toolchain now requires Python 3.11. "
    "Also confirmed: judging is done by Qwen and Alibaba Cloud engineers."
)

QUESTIONS = [
    "When is the submission deadline and how soon is it?",
    "What Python version should we use for the build scripts?",
    "How many members can a team have, and which model must we use?",
]
