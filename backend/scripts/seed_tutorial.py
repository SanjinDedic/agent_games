"""Seed THE tutorial: 10 exercises building up to a Greedy Pig agent.

The progression starts at basic dictionary lookups and rounding, and ends
with parsing the real nested `game_state` dictionary that Greedy Pig passes
to `make_decision`.

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
    Tutorial,
)
from backend.database.db_session import get_db_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TUTORIAL_TITLE = "Python Foundations for Greedy Pig"
TUTORIAL_DESCRIPTION = (
    "Ten short exercises that build every Python skill you need to write a "
    "winning Greedy Pig agent. You start with simple dictionary lookups and "
    "rounding, and finish by parsing the real nested game_state dictionary "
    "and making a banking decision from it. Each exercise gives you a "
    "problem, starter code, and test cases — submit your code to see which "
    "tests pass."
)


# ---------------------------------------------------------------------------
# Exercise definitions, in teaching order. Each test case is
# {"name": str, "args": [...], "expected": ...}; the exercise worker calls
# the entry function with `args` and compares the return value with ==.
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
        "test_cases": [
            {
                "name": "reads Alice's money",
                "args": [{"Alice": 30, "Bob": 55}, "Alice"],
                "expected": 30,
            },
            {
                "name": "reads Bob's money",
                "args": [{"Alice": 30, "Bob": 55}, "Bob"],
                "expected": 55,
            },
            {
                "name": "missing player returns 0",
                "args": [{"Alice": 30}, "Zoe"],
                "expected": 0,
            },
            {
                "name": "empty scoreboard returns 0",
                "args": [{}, "Alice"],
                "expected": 0,
            },
        ],
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
        "test_cases": [
            {
                "name": "two players split 10",
                "args": [10, 2],
                "expected": 5.0,
            },
            {
                "name": "three players split 10",
                "args": [10, 3],
                "expected": 3.33,
            },
            {
                "name": "one player keeps it all",
                "args": [10, 1],
                "expected": 10.0,
            },
            {
                "name": "two players split 7",
                "args": [7, 2],
                "expected": 3.5,
            },
            {
                "name": "three players split 20",
                "args": [20, 3],
                "expected": 6.67,
            },
        ],
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
        "test_cases": [
            {
                "name": "well over the threshold banks",
                "args": [25, 20],
                "expected": "bank",
            },
            {
                "name": "under the threshold continues",
                "args": [12, 20],
                "expected": "continue",
            },
            {
                "name": "exactly on the threshold banks",
                "args": [20, 20],
                "expected": "bank",
            },
            {
                "name": "nothing unbanked continues",
                "args": [0, 15],
                "expected": "continue",
            },
        ],
    },
    # 4 ------------------------------------------------------------------
    {
        "title": "My Total Money",
        "entry_function": "total_money",
        "problem_markdown": """\
# My Total Money

Greedy Pig keeps your money in **two** dictionaries: `banked_money`
(safe, counts toward winning) and `unbanked_money` (at risk — one bad
roll and it's gone). To know how rich a player really is right now, you
add their entry from each dictionary together.

## The Task

Write a function `total_money(banked_money, unbanked_money, name)` that
returns the player's banked money plus their unbanked money.

Both dictionaries always contain `name`.

## Examples

```python
total_money({"Alice": 40, "Bob": 10}, {"Alice": 7, "Bob": 0}, "Alice")
# 47

total_money({"Alice": 40, "Bob": 10}, {"Alice": 7, "Bob": 0}, "Bob")
# 10
```

## Hints

- Look `name` up in each dictionary separately, then add the two numbers.
""",
        "starter_code": """\
def total_money(banked_money, unbanked_money, name):
    # Add the player's banked money and unbanked money together.
    pass  # Replace this line with your code
""",
        "test_cases": [
            {
                "name": "banked plus unbanked",
                "args": [{"Alice": 40, "Bob": 10}, {"Alice": 7, "Bob": 0}, "Alice"],
                "expected": 47,
            },
            {
                "name": "zero unbanked adds nothing",
                "args": [{"Alice": 40, "Bob": 10}, {"Alice": 7, "Bob": 0}, "Bob"],
                "expected": 10,
            },
            {
                "name": "all money still unbanked",
                "args": [{"Cara": 0}, {"Cara": 22}, "Cara"],
                "expected": 22,
            },
            {
                "name": "flat broke",
                "args": [{"Dana": 0}, {"Dana": 0}, "Dana"],
                "expected": 0,
            },
        ],
    },
    # 5 ------------------------------------------------------------------
    {
        "title": "Money on the Table",
        "entry_function": "pot_size",
        "problem_markdown": """\
# Money on the Table

Sometimes an agent cares about the whole table, not just itself. How much
unbanked money is at risk right now across **all** players? If the next
roll is a 1, all of it vanishes.

## The Task

Write a function `pot_size(unbanked_money)` that returns the sum of every
value in the dictionary. An empty dictionary means nothing is at risk, so
return `0`.

## Examples

```python
pot_size({"Alice": 5, "Bob": 12, "Cara": 0})
# 17

pot_size({})
# 0
```

## Hints

- `unbanked_money.values()` gives you just the amounts, without the names.
- You can loop over them and add to a running total —
  or look up what Python's built-in `sum()` does.
""",
        "starter_code": """\
def pot_size(unbanked_money):
    # Add up every amount in the dictionary and return the total.
    pass  # Replace this line with your code
""",
        "test_cases": [
            {
                "name": "adds three players' piles",
                "args": [{"Alice": 5, "Bob": 12, "Cara": 0}],
                "expected": 17,
            },
            {
                "name": "single player",
                "args": [{"Alice": 31}],
                "expected": 31,
            },
            {
                "name": "empty table is 0",
                "args": [{}],
                "expected": 0,
            },
            {
                "name": "everyone just banked",
                "args": [{"Alice": 0, "Bob": 0}],
                "expected": 0,
            },
        ],
    },
    # 6 ------------------------------------------------------------------
    {
        "title": "Find the Leader",
        "entry_function": "find_leader",
        "problem_markdown": """\
# Find the Leader

Good agents play differently when they are winning than when they are
chasing. Step one of that: work out **who** is in front. Here you find the
name of the player with the most banked money.

## The Task

Write a function `find_leader(banked_money)` that returns the **name**
(the key, not the amount) of the player with the highest banked money.

The dictionary is never empty, and in every test exactly one player is in
the lead — you don't need to handle ties.

## Examples

```python
find_leader({"Alice": 30, "Bob": 55, "Cara": 41})
# "Bob"

find_leader({"Alice": 90})
# "Alice"
```

## Hints

- `for name in banked_money:` loops over the names;
  `banked_money[name]` gives each one's amount.
- Keep two variables while you loop: the best name so far and the best
  amount so far. Update both whenever you see a bigger amount.
""",
        "starter_code": """\
def find_leader(banked_money):
    # Return the NAME of the player with the most banked money.
    # Loop over the dictionary and track the best name you have
    # seen so far, and how much money that player had.
    pass  # Replace this line with your code
""",
        "test_cases": [
            {
                "name": "leader in the middle",
                "args": [{"Alice": 30, "Bob": 55, "Cara": 41}],
                "expected": "Bob",
            },
            {
                "name": "leader listed first",
                "args": [{"Dana": 72, "Eli": 4, "Flo": 40}],
                "expected": "Dana",
            },
            {
                "name": "leader listed last",
                "args": [{"Alice": 12, "Bob": 15, "Cara": 60}],
                "expected": "Cara",
            },
            {
                "name": "only one player",
                "args": [{"Alice": 90}],
                "expected": "Alice",
            },
        ],
    },
    # 7 ------------------------------------------------------------------
    {
        "title": "Still Rolling",
        "entry_function": "still_rolling",
        "problem_markdown": """\
# Still Rolling

Greedy Pig's `game_state` includes `players_banked_this_round` — a
**list** of the players who have already banked and are safely out of the
round. Everyone else is still rolling and still at risk. Knowing how many
rivals are still in the round is a key strategic signal.

## The Task

Write a function `still_rolling(players, players_banked_this_round)` that
returns a **list** of the names in `players` that are *not* in
`players_banked_this_round`, keeping the same order as `players`.

## Examples

```python
still_rolling(["Alice", "Bob", "Cara"], ["Bob"])
# ["Alice", "Cara"]

still_rolling(["Alice", "Bob"], [])
# ["Alice", "Bob"]

still_rolling(["Alice", "Bob"], ["Alice", "Bob"])
# []
```

## Hints

- `in` and `not in` work on lists too: `"Bob" not in banked` is `True`
  when Bob hasn't banked.
- Start with an empty list and `append` the names that should keep
  rolling.
""",
        "starter_code": """\
def still_rolling(players, players_banked_this_round):
    # Build and return a list of the players who have NOT banked yet,
    # in the same order they appear in `players`.
    pass  # Replace this line with your code
""",
        "test_cases": [
            {
                "name": "one player has banked",
                "args": [["Alice", "Bob", "Cara"], ["Bob"]],
                "expected": ["Alice", "Cara"],
            },
            {
                "name": "nobody has banked yet",
                "args": [["Alice", "Bob"], []],
                "expected": ["Alice", "Bob"],
            },
            {
                "name": "everyone has banked",
                "args": [["Alice", "Bob"], ["Alice", "Bob"]],
                "expected": [],
            },
            {
                "name": "keeps the original order",
                "args": [["Dana", "Eli", "Flo", "Gus"], ["Eli", "Dana"]],
                "expected": ["Flo", "Gus"],
            },
        ],
    },
    # 8 ------------------------------------------------------------------
    {
        "title": "Everyone's Total",
        "entry_function": "all_totals",
        "problem_markdown": """\
# Everyone's Total

You already added banked + unbanked for **one** player. A serious agent
sizes up the *whole table* at once: it builds a **new dictionary** with
every player's true total. This "combine two dictionaries into one" move
is the heart of ranking players, which comes next.

## The Task

Write a function `all_totals(banked_money, unbanked_money)` that returns
a **new dictionary** mapping every player's name to their banked money
plus their unbanked money.

Both dictionaries always contain exactly the same names.

## Examples

```python
all_totals({"Alice": 40, "Bob": 10}, {"Alice": 7, "Bob": 5})
# {"Alice": 47, "Bob": 15}
```

## Hints

- Start with an empty dictionary: `totals = {}`.
- Loop over the names in `banked_money`, and for each name store
  `totals[name] = ...`.
""",
        "starter_code": """\
def all_totals(banked_money, unbanked_money):
    # Return a NEW dictionary: every player's name mapped to
    # their banked money plus their unbanked money.
    pass  # Replace this line with your code
""",
        "test_cases": [
            {
                "name": "combines two players",
                "args": [{"Alice": 40, "Bob": 10}, {"Alice": 7, "Bob": 5}],
                "expected": {"Alice": 47, "Bob": 15},
            },
            {
                "name": "three players, some zeros",
                "args": [
                    {"Alice": 0, "Bob": 20, "Cara": 55},
                    {"Alice": 13, "Bob": 0, "Cara": 6},
                ],
                "expected": {"Alice": 13, "Bob": 20, "Cara": 61},
            },
            {
                "name": "single player",
                "args": [{"Dana": 33}, {"Dana": 9}],
                "expected": {"Dana": 42},
            },
        ],
    },
    # 9 ------------------------------------------------------------------
    {
        "title": "What's My Rank?",
        "entry_function": "my_rank",
        "problem_markdown": """\
# What's My Rank?

Now for the real thing. Greedy Pig passes your agent one **nested**
dictionary called `game_state`. The money dictionaries you've been
working with live *inside* it:

```python
game_state = {
    "round_no": 3,
    "roll_no": 2,
    "players_banked_this_round": [],
    "banked_money": {"Alice": 40, "Bob": 55, "Cara": 10},
    "unbanked_money": {"Alice": 20, "Bob": 0, "Cara": 12},
}
```

So `game_state["banked_money"]["Bob"]` digs two levels down to get 55.

The built-in `Player` class in Greedy Pig has a `my_rank` helper — here
you build it yourself so you understand exactly what it does.

## The Task

Write a function `my_rank(game_state, name)` that returns the player's
rank by **total** money (banked + unbanked): `1` means the richest player
at the table, `2` the second richest, and so on.

In every test exactly one player holds each rank — no ties.

In the example above the totals are Alice 60, Bob 55, Cara 22, so
`my_rank(game_state, "Alice")` is `1` even though Bob has more *banked* —
unbanked money still counts toward rank.

## Hints

- Pull out the inner dictionaries first:
  `banked = game_state["banked_money"]`.
- Build each player's total, exactly like *Everyone's Total*.
- Count how many players have a total **bigger** than yours — your rank
  is that count plus 1. (Sorting the totals works too.)
""",
        "starter_code": """\
def my_rank(game_state, name):
    # Step 1: get the "banked_money" and "unbanked_money"
    #         dictionaries out of game_state.
    # Step 2: work out every player's total money.
    # Step 3: return this player's rank: 1 = richest at the table.
    pass  # Replace this line with your code
""",
        "test_cases": [
            {
                "name": "highest total is rank 1",
                "args": [
                    {
                        "round_no": 3,
                        "roll_no": 2,
                        "players_banked_this_round": [],
                        "banked_money": {"Alice": 40, "Bob": 55, "Cara": 10},
                        "unbanked_money": {"Alice": 20, "Bob": 0, "Cara": 12},
                    },
                    "Alice",
                ],
                "expected": 1,
            },
            {
                "name": "most banked is not always rank 1",
                "args": [
                    {
                        "round_no": 3,
                        "roll_no": 2,
                        "players_banked_this_round": [],
                        "banked_money": {"Alice": 40, "Bob": 55, "Cara": 10},
                        "unbanked_money": {"Alice": 20, "Bob": 0, "Cara": 12},
                    },
                    "Bob",
                ],
                "expected": 2,
            },
            {
                "name": "poorest player is last",
                "args": [
                    {
                        "round_no": 3,
                        "roll_no": 2,
                        "players_banked_this_round": [],
                        "banked_money": {"Alice": 40, "Bob": 55, "Cara": 10},
                        "unbanked_money": {"Alice": 20, "Bob": 0, "Cara": 12},
                    },
                    "Cara",
                ],
                "expected": 3,
            },
            {
                "name": "unbanked money can put you in front",
                "args": [
                    {
                        "round_no": 7,
                        "roll_no": 5,
                        "players_banked_this_round": ["Dana"],
                        "banked_money": {"Dana": 70, "Eli": 45},
                        "unbanked_money": {"Dana": 0, "Eli": 30},
                    },
                    "Eli",
                ],
                "expected": 1,
            },
            {
                "name": "banking early can cost the lead",
                "args": [
                    {
                        "round_no": 7,
                        "roll_no": 5,
                        "players_banked_this_round": ["Dana"],
                        "banked_money": {"Dana": 70, "Eli": 45},
                        "unbanked_money": {"Dana": 0, "Eli": 30},
                    },
                    "Dana",
                ],
                "expected": 2,
            },
        ],
    },
    # 10 -----------------------------------------------------------------
    {
        "title": "Make the Decision",
        "entry_function": "make_decision",
        "problem_markdown": """\
# Make the Decision

The capstone. This is (almost) exactly the method a real Greedy Pig agent
implements: read the nested `game_state`, do some arithmetic, and answer
`"bank"` or `"continue"`. The only difference is that in the real game
your name arrives as `self.name` — here it is passed in as an argument.

## The Task

Write a function `make_decision(game_state, name)` that applies these
rules **in order** and returns the first one that fires:

1. If banking now would give you 100 or more banked in total
   (your banked + your unbanked ≥ 100) → return `"bank"` — that wins the
   game!
2. If your unbanked money is 30 or more → return `"bank"` — too much to
   risk on one roll.
3. If **2 or more** players have already banked this round *and* your
   unbanked money is 15 or more → return `"bank"` — the odds no longer
   favour the greedy.
4. Otherwise → return `"continue"`.

`game_state` has the full shape you saw in *What's My Rank?*:
`round_no`, `roll_no`, `players_banked_this_round` (a list),
`banked_money` and `unbanked_money` (nested dictionaries).

## Examples

```python
game_state = {
    "round_no": 9,
    "roll_no": 4,
    "players_banked_this_round": [],
    "banked_money": {"Alice": 80, "Bob": 60},
    "unbanked_money": {"Alice": 25, "Bob": 10},
}

make_decision(game_state, "Alice")
# "bank"      (80 + 25 = 105 — banking now wins)

make_decision(game_state, "Bob")
# "continue"  (70 total, only 10 at risk, nobody has banked)
```

## Hints

- Dig your two numbers out first:
  `my_banked = game_state["banked_money"][name]` and the same for
  unbanked. The rules become one short `if`/`elif`/`else` chain.
- `len(game_state["players_banked_this_round"])` counts how many players
  have banked this round.
- Check the rules in the order given — rule 1 beats rule 4 even on
  roll 1.
""",
        "starter_code": """\
def make_decision(game_state, name):
    # Step 1: get YOUR banked and unbanked money out of the
    #         nested dictionaries in game_state.
    # Step 2: count how many players have banked this round.
    # Step 3: apply the four rules from the problem, in order,
    #         and return "bank" or "continue".
    pass  # Replace this line with your code
""",
        "test_cases": [
            {
                "name": "banking now wins the game",
                "args": [
                    {
                        "round_no": 9,
                        "roll_no": 4,
                        "players_banked_this_round": [],
                        "banked_money": {"Alice": 80, "Bob": 60},
                        "unbanked_money": {"Alice": 25, "Bob": 10},
                    },
                    "Alice",
                ],
                "expected": "bank",
            },
            {
                "name": "safe position keeps rolling",
                "args": [
                    {
                        "round_no": 9,
                        "roll_no": 4,
                        "players_banked_this_round": [],
                        "banked_money": {"Alice": 80, "Bob": 60},
                        "unbanked_money": {"Alice": 25, "Bob": 10},
                    },
                    "Bob",
                ],
                "expected": "continue",
            },
            {
                "name": "30 unbanked is too much to risk",
                "args": [
                    {
                        "round_no": 2,
                        "roll_no": 6,
                        "players_banked_this_round": ["Cara"],
                        "banked_money": {"Alice": 10, "Bob": 20, "Cara": 30},
                        "unbanked_money": {"Alice": 30, "Bob": 14, "Cara": 0},
                    },
                    "Alice",
                ],
                "expected": "bank",
            },
            {
                "name": "one banker is not enough pressure",
                "args": [
                    {
                        "round_no": 2,
                        "roll_no": 6,
                        "players_banked_this_round": ["Cara"],
                        "banked_money": {"Alice": 10, "Bob": 20, "Cara": 30},
                        "unbanked_money": {"Alice": 30, "Bob": 14, "Cara": 0},
                    },
                    "Bob",
                ],
                "expected": "continue",
            },
            {
                "name": "two bankers plus 15 unbanked banks",
                "args": [
                    {
                        "round_no": 5,
                        "roll_no": 3,
                        "players_banked_this_round": ["Bob", "Cara"],
                        "banked_money": {
                            "Alice": 50,
                            "Bob": 40,
                            "Cara": 35,
                            "Dan": 20,
                        },
                        "unbanked_money": {
                            "Alice": 15,
                            "Bob": 0,
                            "Cara": 0,
                            "Dan": 8,
                        },
                    },
                    "Alice",
                ],
                "expected": "bank",
            },
            {
                "name": "two bankers but a small pile rolls on",
                "args": [
                    {
                        "round_no": 5,
                        "roll_no": 3,
                        "players_banked_this_round": ["Bob", "Cara"],
                        "banked_money": {
                            "Alice": 50,
                            "Bob": 40,
                            "Cara": 35,
                            "Dan": 20,
                        },
                        "unbanked_money": {
                            "Alice": 15,
                            "Bob": 0,
                            "Cara": 0,
                            "Dan": 8,
                        },
                    },
                    "Dan",
                ],
                "expected": "continue",
            },
        ],
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
                    test_cases=[],
                )
            exercise.order_index = index
            exercise.title = spec["title"]
            exercise.problem_markdown = spec["problem_markdown"]
            exercise.starter_code = spec["starter_code"]
            exercise.entry_function = spec["entry_function"]
            exercise.test_cases = spec["test_cases"]
            session.add(exercise)

        for leftover in existing[len(EXERCISES):]:
            logger.info(f"Deleting leftover exercise '{leftover.title}'")
            _delete_exercise(session, leftover)

        session.commit()
        logger.info(
            f"Seeded tutorial id={tutorial.id} with {len(EXERCISES)} exercises"
        )
    return True


if __name__ == "__main__":
    raise SystemExit(0 if seed_tutorial() else 1)
