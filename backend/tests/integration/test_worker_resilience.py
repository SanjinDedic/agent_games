"""Worker resilience under hostile agents (Celery migration sanity checks).

These agents PASS the AST safety check (validate_code) — no blocked imports or
calls — so they reach a real worker child and detonate there. They probe the two
resource-exhaustion modes the platform must survive:

1. Memory bomb via recursion. Each recursive frame doubles a bytearray and
   pins it in class-level state, so the worker's cgroup (compose mem_limit:
   500m, shared across --concurrency=4) is exhausted in ~9 frames — long before
   Python's ~1000-frame recursion limit. The kernel OOM killer SIGKILLs the
   child; billiard surfaces that to .get() as WorkerLostError. Pinning the
   payload in class state is deliberate: a bare recursion that raised
   MemoryError would be swallowed by the game engine's `except Exception`, so
   the persistent hoard guarantees the cgroup — not Python — wins the race.

2. CPU bomb. A busy loop that also swallows exceptions inside itself, so the
   soft-limit SoftTimeLimitExceeded cannot stop it. Only the hard time_limit=8
   SIGKILL backstop kills it; .get() raises TimeLimitExceeded.

The point of each test is NOT just that the bomb dies — it's that the pool
RECOVERS. worker_max_tasks_per_child=1 already retires the child; after a
hostile task the very next validation on the same queue must still succeed.
"""

import pytest
from billiard.exceptions import WorkerLostError
from celery.exceptions import TimeLimitExceeded

from backend.routes.user.code_validation import run_validation, validate_code

# --- Hostile agents (both pass the AST safety check) ------------------------

# Infinite memory through recursion. `_hoard` is class-level so the doubled
# payloads survive even if a MemoryError is raised and swallowed mid-flight —
# the container's memory cap, not Python, is what terminates the child.
MEMORY_BOMB_RECURSION = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    _hoard = []

    def make_decision(self, game_state):
        def grow(chunk):
            CustomPlayer._hoard.append(chunk)   # pin it so it can't be freed
            return grow(chunk + chunk)          # double every frame
        grow(bytearray(1024 * 1024))            # start at 1 MB
        return "bank"
"""

# Infinite processing power. The inner try/except swallows the soft-limit
# SoftTimeLimitExceeded (a plain Exception), so the loop never yields; only the
# hard time_limit SIGKILL stops it.
CPU_BOMB = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        while True:
            try:
                n = 0
                for i in range(10 ** 8):
                    n += i * i
            except Exception:
                continue
"""

# A normal, well-behaved agent used to prove the worker recovers afterwards.
VALID_PROBE = """
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def make_decision(self, game_state):
        if game_state["unbanked_money"][self.name] > 20:
            return "bank"
        return "continue"
"""


def _validate(code: str, team: str):
    return run_validation.delay(
        code=code,
        game_name="greedy_pig",
        team_name=team,
        num_simulations=10,
    ).get(timeout=30)


def test_hostile_agents_pass_the_ast_check():
    """Both bombs are 'safe' by AST rules, so they genuinely reach a worker."""
    for code in (MEMORY_BOMB_RECURSION, CPU_BOMB):
        is_safe, message = validate_code(code)
        assert is_safe, f"expected AST-clean, got: {message}"


def test_memory_bomb_is_contained_and_worker_recovers(celery_workers):
    """A recursive memory bomb OOM-kills its child; the pool keeps serving."""
    with pytest.raises(WorkerLostError):
        _validate(MEMORY_BOMB_RECURSION, "mem_bomb_team")

    # The offending child is gone (SIGKILL). A fresh child must take the next
    # task — this is the resilience guarantee the Celery migration must keep.
    result = _validate(VALID_PROBE, "recovery_after_mem")
    assert result["status"] == "success", result


def test_cpu_bomb_is_hard_killed_and_worker_recovers(celery_workers):
    """A soft-limit-swallowing busy loop is hard-killed; the pool keeps serving."""
    with pytest.raises(TimeLimitExceeded):
        _validate(CPU_BOMB, "cpu_bomb_team")

    result = _validate(VALID_PROBE, "recovery_after_cpu")
    assert result["status"] == "success", result
