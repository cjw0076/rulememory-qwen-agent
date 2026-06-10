"""GPU smoke test for the REAL local Qwen reasoner.

Skipped automatically unless a CUDA GPU + transformers are available and
RULEMEMORY_RUN_GPU=1 is set, so the default CI run stays GPU-free.

Run explicitly:
    RULEMEMORY_RUN_GPU=1 /home/user/miniconda3/envs/dacon_vlm/bin/python \
        -m pytest tests/test_local_qwen_gpu.py -v -s
"""

import os
import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))


def _gpu_available() -> bool:
    if os.environ.get("RULEMEMORY_RUN_GPU") != "1":
        return False
    try:
        import torch  # noqa
        import transformers  # noqa

        return torch.cuda.is_available()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _gpu_available(),
    reason="set RULEMEMORY_RUN_GPU=1 with a CUDA GPU + transformers to run real Qwen",
)


def test_real_qwen_extracts_and_answers():
    from rulememory_qwen.reasoner import QwenLocalReasoner

    r = QwenLocalReasoner()
    facts = r.extract_facts(
        "The submission deadline is 2026-07-10. We should still use Python 2."
    )
    assert facts, "Qwen should extract at least one fact"
    types = {f["type"] for f in facts}
    assert types & {"deadline", "assumption", "rule", "fact"}
    ans = r.answer("what is the deadline?", facts)
    assert "2026" in ans["answer"]
