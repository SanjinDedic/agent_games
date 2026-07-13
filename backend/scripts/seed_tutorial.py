"""Seed THE tutorial: 5 exercises building up to a Greedy Pig agent.

The progression starts at basic dictionary lookups and rounding, then covers
printing output and splitting logic across helper functions — the shape of a
real agent's decision code.

Every exercise's tests are a Python test script (`Exercise.test_code`) run by
backend/tasks/exercise_test_code.py: `test_*` functions calling the student's
functions by name, recording results with the injected `check`,
`check_output`, and `capture` helpers. The scripts are admin-trusted and
seed-managed — students never see or touch them.

Idempotent overwrite: the platform has exactly one tutorial, so this script
reuses the oldest Tutorial row (deleting any others), overwrites its title
and description, and rewrites its exercises in place. Exercises are matched
by position (order_index), so re-running after editing content updates the
same rows; leftover exercises beyond the new count are deleted along with
their submission history.

Run inside the api container:
    docker compose exec api python -m backend.scripts.seed_tutorial
"""

import logging
import os
import sys

from dotenv import load_dotenv
from sqlmodel import Session, select

load_dotenv()

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from backend.database.db_models import (
    Exercise,
    ExerciseSubmissionMetadata,
    League,
    LeagueTutorial,
    Tutorial,
)
from backend.database.db_session import get_db_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TUTORIAL_TITLE = "Python Foundations for Greedy Pig"
TUTORIAL_DESCRIPTION = (
    "Five short exercises that build every Python skill you need to write a "
    "winning Greedy Pig agent. You start with simple dictionary lookups and "
    "rounding, then learn to print a scoreboard and to split a decision "
    "across helper functions — exactly how a real agent is built. Each "
    "exercise gives you a problem, starter code, and tests — submit your "
    "code to see which tests pass."
)


# ---------------------------------------------------------------------------
# Exercise definitions, in teaching order. Each spec's `test_code` is a
# trusted Python test script exec'd into the same namespace as the student's
# code; see backend/tasks/exercise_test_code.py for the helper API.
# ---------------------------------------------------------------------------

EXERCISES = [
    # 1 ------------------------------------------------------------------
    {
        "title": "Read the Scoreboard",
        "entry_function": "get_banked",
        "problem_markdown": """\
# Read the Scoreboard

In Greedy Pig the game hands your agent dictionaries like
`{"Alice": 30, "Bob": 55}` — each player's name mapped to their money.
Reading a value out of a dictionary is the single most common thing an
agent does, so it is where we start.

## The Task

Write a function `get_banked(banked_money, name)` that returns the amount
of money stored for `name` in the `banked_money` dictionary.

If `name` is **not** in the dictionary, return `0` instead of crashing.

## Examples

```python
get_banked({"Alice": 30, "Bob": 55}, "Alice")
# 30

get_banked({"Alice": 30, "Bob": 55}, "Bob")
# 55

get_banked({"Alice": 30}, "Zoe")
# 0
```

## Hints

- `banked_money[name]` looks up a value — but crashes if the key is missing.
- `banked_money.get(name, 0)` looks up a value and falls back to `0`.
- You can also check first: `if name in banked_money:`
""",
        "starter_code": """\
def get_banked(banked_money, name):
    # banked_money is a dictionary like {"Alice": 30, "Bob": 55}.
    # Return the amount stored for `name`.
    # If `name` is not in the dictionary, return 0.
    pass  # Replace this line with your code
""",
        "test_code": """\
def test_reads_alice():
    \"\"\"reads Alice's money\"\"\"
    check(get_banked({"Alice": 30, "Bob": 55}, "Alice"), 30)


def test_reads_bob():
    \"\"\"reads Bob's money\"\"\"
    check(get_banked({"Alice": 30, "Bob": 55}, "Bob"), 55)


def test_missing_player():
    \"\"\"missing player returns 0\"\"\"
    check(get_banked({"Alice": 30}, "Zoe"), 0)


def test_empty_scoreboard():
    \"\"\"empty scoreboard returns 0\"\"\"
    check(get_banked({}, "Alice"), 0)
""",
    },
    # 2 ------------------------------------------------------------------
    {
        "title": "Split the Prize",
        "entry_function": "split_reward",
        "problem_markdown": """\
# Split the Prize

When Greedy Pig players tie, they **split the reward pool equally**, and
the game engine rounds each share to 2 decimal places. Two players tied
for a 10-point prize get 5.0 each; three players get 3.33 each.

## The Task

Write a function `split_reward(pool, num_players)` that divides `pool`
equally between `num_players` players and returns one player's share,
**rounded to 2 decimal places**.

## Examples

```python
split_reward(10, 2)
# 5.0

split_reward(10, 3)
# 3.33

split_reward(7, 2)
# 3.5
```

## Hints

- `/` is normal division: `10 / 4` gives `2.5`.
- `round(value, 2)` rounds to 2 decimal places: `round(3.333, 2)` gives `3.33`.
""",
        "starter_code": """\
def split_reward(pool, num_players):
    # Divide the pool equally between the players,
    # then round one share to 2 decimal places.
    pass  # Replace this line with your code
""",
        "test_code": """\
def test_two_players_split_10():
    \"\"\"two players split 10\"\"\"
    check(split_reward(10, 2), 5.0)


def test_three_players_split_10():
    \"\"\"three players split 10\"\"\"
    check(split_reward(10, 3), 3.33)


def test_one_player_keeps_it_all():
    \"\"\"one player keeps it all\"\"\"
    check(split_reward(10, 1), 10.0)


def test_two_players_split_7():
    \"\"\"two players split 7\"\"\"
    check(split_reward(7, 2), 3.5)


def test_three_players_split_20():
    \"\"\"three players split 20\"\"\"
    check(split_reward(20, 3), 6.67)
""",
    },
    # 3 ------------------------------------------------------------------
    {
        "title": "Bank or Roll?",
        "entry_function": "should_bank",
        "problem_markdown": """\
# Bank or Roll?

A Greedy Pig agent answers one question over and over: keep rolling, or
bank what I have? Its answer is always one of two strings: `"bank"` or
`"continue"`. The simplest possible strategy banks once its unbanked pile
reaches some threshold.

## The Task

Write a function `should_bank(unbanked, threshold)` that returns:

- `"bank"` if `unbanked` is greater than or equal to `threshold`
- `"continue"` otherwise

Note: reaching the threshold exactly counts — `should_bank(20, 20)` is
`"bank"`.

## Examples

```python
should_bank(25, 20)
# "bank"

should_bank(12, 20)
# "continue"

should_bank(20, 20)
# "bank"
```

## Hints

- `>=` means "greater than or equal to".
- Return the strings exactly as written: `"bank"` and `"continue"` —
  spelling and lowercase matter.
""",
        "starter_code": """\
def should_bank(unbanked, threshold):
    # Return "bank" if unbanked has reached the threshold,
    # otherwise return "continue".
    pass  # Replace this line with your code
""",
        "test_code": """\
def test_over_threshold():
    \"\"\"well over the threshold banks\"\"\"
    check(should_bank(25, 20), "bank")


def test_under_threshold():
    \"\"\"under the threshold continues\"\"\"
    check(should_bank(12, 20), "continue")


def test_exactly_on_threshold():
    \"\"\"exactly on the threshold banks\"\"\"
    check(should_bank(20, 20), "bank")


def test_nothing_unbanked():
    \"\"\"nothing unbanked continues\"\"\"
    check(should_bank(0, 15), "continue")
""",
    },
    # 4 ------------------------------------------------------------------
    {
        "title": "Announce the Scores",
        "entry_function": "print_scoreboard",
        "problem_markdown": """\
# Announce the Scores

So far your functions have **returned** values. This one is different: it
**prints**. After every round, Greedy Pig announces the scoreboard — and
printing is also how you'll debug your own agent, so it's worth getting
right.

## The Task

Write a function `print_scoreboard(banked_money)` that prints one line
per player, in the dictionary's order, in exactly this format:

```
name: amount
```

The function should print — not return — the lines. It should return
nothing.

## Examples

```python
print_scoreboard({"Alice": 30, "Bob": 55})
# prints:
# Alice: 30
# Bob: 55

print_scoreboard({"Cara": 12})
# prints:
# Cara: 12
```

## Hints

- Loop over the players: `for name in banked_money:` — or over
  `banked_money.items()` to get name and amount together.
- An f-string builds the line: `f"{name}: {amount}"`.
- `print(...)` each line — don't collect them into a string and return it.
""",
        "starter_code": """\
def print_scoreboard(banked_money):
    # Print one line per player, like
    #   Alice: 30
    # in the dictionary's order. Print, don't return!
    pass  # Replace this line with your code
""",
        "test_code": """\
def test_two_players():
    \"\"\"prints one line per player, in order\"\"\"
    with capture() as out:
        print_scoreboard({"Alice": 30, "Bob": 55})
    check_output(out.text, "Alice: 30\\nBob: 55")


def test_single_player():
    \"\"\"a single player prints a single line\"\"\"
    with capture() as out:
        print_scoreboard({"Cara": 12})
    check_output(out.text, "Cara: 12")


def test_empty_scoreboard():
    \"\"\"an empty scoreboard prints nothing\"\"\"
    with capture() as out:
        print_scoreboard({})
    check_output(out.text, "")


def test_prints_not_returns():
    \"\"\"the function prints instead of returning\"\"\"
    with capture() as out:
        result = print_scoreboard({"Alice": 30})
    check(result, None, name="returns None (print, don't return)")
""",
    },
    # 5 ------------------------------------------------------------------
    {
        "title": "Safe to Roll?",
        "entry_function": "decide",
        "problem_markdown": """\
# Safe to Roll?

Real agents don't cram everything into one function — they split their
thinking into **helpers**. Here you write two functions, and the second
one calls the first.

## The Task

Write **both** of these functions:

1. `is_safe(unbanked)` — returns `True` if `unbanked` is less than `20`,
   otherwise `False`. (At 20 or more, one bad roll loses too much.)

2. `decide(unbanked, banked)` — applies these rules **in order** and
   returns the first one that fires:
   1. If banking now would reach 100 or more in total
      (`banked + unbanked >= 100`) → return `"bank"` — that wins the game!
   2. If `is_safe(unbanked)` says it's safe → return `"continue"`.
   3. Otherwise → return `"bank"`.

`decide` must **call** `is_safe` — the tests check both functions, and
they check that `decide` agrees with your `is_safe`.

## Examples

```python
is_safe(5)
# True

is_safe(20)
# False

decide(5, 10)
# "continue"   (safe pile, nowhere near 100)

decide(25, 10)
# "bank"       (25 unbanked is not safe)

decide(10, 95)
# "bank"       (95 + 10 = 105 — banking now wins)
```

## Hints

- `unbanked < 20` is already a True/False value — you can return it
  directly.
- In `decide`, check the winning rule first, then use
  `if is_safe(unbanked):` for the second rule.
""",
        "starter_code": """\
def is_safe(unbanked):
    # True if the unbanked pile is still small enough to risk (< 20).
    pass  # Replace this line with your code


def decide(unbanked, banked):
    # Rule 1: banking now wins (banked + unbanked >= 100) -> "bank"
    # Rule 2: still safe to roll (use is_safe!)          -> "continue"
    # Rule 3: otherwise                                   -> "bank"
    pass  # Replace this line with your code
""",
        "test_code": """\
def test_is_safe_small_piles():
    \"\"\"is_safe: a small pile is safe\"\"\"
    check(is_safe(5), True, name="is_safe(5) is True")
    check(is_safe(19), True, name="is_safe(19) is True")


def test_is_safe_big_piles():
    \"\"\"is_safe: 20 or more is not safe\"\"\"
    check(is_safe(20), False, name="is_safe(20) is False")
    check(is_safe(35), False, name="is_safe(35) is False")


def test_decide_rules():
    \"\"\"decide applies the three rules in order\"\"\"
    check(decide(5, 10), "continue", name='decide(5, 10) is "continue"')
    check(decide(25, 10), "bank", name='decide(25, 10) is "bank"')
    check(decide(10, 95), "bank", name='decide(10, 95) wins the game')
    check(decide(19, 50), "continue", name='decide(19, 50) is "continue"')


def test_decide_agrees_with_is_safe():
    \"\"\"decide follows is_safe when the game can't be won yet\"\"\"
    for unbanked in (3, 12, 19, 20, 28):
        expected = "continue" if is_safe(unbanked) else "bank"
        check(
            decide(unbanked, 10),
            expected,
            name=f"decide({unbanked}, 10) agrees with is_safe({unbanked})",
        )
""",
    },
]


def _delete_exercise(session: Session, exercise: Exercise) -> None:
    """Delete an exercise along with the submission rows that reference it."""
    metas = session.exec(
        select(ExerciseSubmissionMetadata).where(
            ExerciseSubmissionMetadata.exercise_id == exercise.id
        )
    ).all()
    for meta in metas:
        if meta.submission:
            session.delete(meta.submission)
        session.delete(meta)
    session.delete(exercise)


def seed_tutorial() -> bool:
    engine = get_db_engine()
    with Session(engine) as session:
        tutorials = session.exec(select(Tutorial).order_by(Tutorial.id)).all()

        # The platform has exactly one tutorial: reuse the oldest row and
        # remove any others, whatever they were called.
        tutorial = tutorials[0] if tutorials else None
        for extra in tutorials[1:]:
            logger.info(f"Deleting extra tutorial '{extra.title}'")
            for exercise in list(extra.exercises):
                _delete_exercise(session, exercise)
            for link in session.exec(
                select(LeagueTutorial).where(
                    LeagueTutorial.tutorial_id == extra.id
                )
            ).all():
                session.delete(link)
            session.delete(extra)

        if tutorial:
            logger.info(
                f"Overwriting tutorial '{tutorial.title}' -> '{TUTORIAL_TITLE}'"
            )
        else:
            logger.info(f"Creating tutorial '{TUTORIAL_TITLE}'")
            tutorial = Tutorial(title=TUTORIAL_TITLE, description="")
        tutorial.title = TUTORIAL_TITLE
        tutorial.description = TUTORIAL_DESCRIPTION
        session.add(tutorial)
        session.flush()

        existing = session.exec(
            select(Exercise)
            .where(Exercise.tutorial_id == tutorial.id)
            .order_by(Exercise.order_index, Exercise.id)
        ).all()

        for index, spec in enumerate(EXERCISES):
            if index < len(existing):
                exercise = existing[index]
                logger.info(f"Overwriting exercise {index}: '{spec['title']}'")
            else:
                logger.info(f"Creating exercise {index}: '{spec['title']}'")
                exercise = Exercise(
                    tutorial_id=tutorial.id,
                    title="",
                    problem_markdown="",
                    entry_function="",
                )
            exercise.order_index = index
            exercise.title = spec["title"]
            exercise.problem_markdown = spec["problem_markdown"]
            exercise.starter_code = spec["starter_code"]
            exercise.entry_function = spec["entry_function"]
            exercise.test_code = spec["test_code"]
            # The seed is a full overwrite: a spec without a solution resets
            # any solution saved through the admin editor.
            exercise.solution = spec.get("solution")
            session.add(exercise)

        for leftover in existing[len(EXERCISES):]:
            logger.info(f"Deleting leftover exercise '{leftover.title}'")
            _delete_exercise(session, leftover)

        # Attach the tutorial to every league that doesn't already have it,
        # so a seeded dev/demo environment shows the tutorial everywhere.
        # (Teams only see tutorials attached to their league.)
        linked_league_ids = set(
            session.exec(
                select(LeagueTutorial.league_id).where(
                    LeagueTutorial.tutorial_id == tutorial.id
                )
            ).all()
        )
        for league_id in session.exec(select(League.id)).all():
            if league_id not in linked_league_ids:
                session.add(
                    LeagueTutorial(league_id=league_id, tutorial_id=tutorial.id)
                )

        session.commit()
        logger.info(
            f"Seeded tutorial id={tutorial.id} with {len(EXERCISES)} exercises"
        )
    return True


if __name__ == "__main__":
    raise SystemExit(0 if seed_tutorial() else 1)
