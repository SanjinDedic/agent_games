"""Seed THE tutorial: 10 exercises building up to a Greedy Pig agent.

The progression is a skill ladder, not a tour of the game: variables and
printing (1), unpacking a list (2-3), unpacking dictionaries of growing
shape (4-6), then reading a real `game_state` and returning a decision (7),
and finally the probability and expected-value reasoning a competitive agent
needs (8-10). Exercise 10 is the agent itself — the same two functions drop
straight into `CustomPlayer.make_decision`.

The numbers are the real game's: a roll of 1 wipes every unbanked pile, faces
2-6 add to it, and banking 100 wins. That makes the expected change from one
roll `(20 - unbanked) / 6`, which crosses zero at 20 — so exercise 9 *derives*
the classic "bank at 20" threshold instead of asserting it.

Every exercise's tests are a Python test script (`Exercise.test_code`) run by
backend/tasks/exercise_test_code.py: `test_*` functions calling the student's
functions by name, recording results with the injected `check`,
`check_output`, and `capture` helpers. The scripts are admin-trusted and
seed-managed — students never see or touch them. Each spec also carries a
`solution`, the reference implementation the admin editor's Run button uses.

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
    "Ten short exercises that build every Python skill you need to write a "
    "winning Greedy Pig agent, one step at a time. You start with variables "
    "and printing, learn to pull values out of lists and dictionaries, then "
    "read a real game state and return a decision. The last three exercises "
    "work out the odds and the expected value of one more roll — and turn "
    "that into an agent you can paste straight into the game. Each exercise "
    "gives you a problem, starter code, and tests — submit your code to see "
    "which tests pass."
)


# ---------------------------------------------------------------------------
# Exercise definitions, in teaching order. Each spec's `test_code` is a
# trusted Python test script exec'd into the same namespace as the student's
# code; see backend/tasks/exercise_test_code.py for the helper API.
# ---------------------------------------------------------------------------

EXERCISES = [
    # 1 ------------------------------------------------------------------
    {
        "title": "Three Variables, One Report",
        "entry_function": "show_rounds",
        "problem_markdown": """\
# Three Variables, One Report

Everything an agent does starts here: put values in **variables**, do some
**arithmetic** with them, and **print** the answer. Printing is also how you
will debug your agent later, so it is worth getting right from the start.

## The Task

Write a function `show_rounds(round1, round2, round3)` that receives the
points you scored in three rounds. It must work out:

- the **total** of the three rounds
- the **average**, rounded to 2 decimal places

and then **print** exactly two lines:

```
Total: 37
Average: 12.33
```

The function prints — it does not return anything.

## Examples

```python
show_rounds(10, 12, 15)
# prints:
# Total: 37
# Average: 12.33

show_rounds(6, 6, 6)
# prints:
# Total: 18
# Average: 6.0
```

Note the second example: an average of exactly 6 still prints as `6.0`,
because dividing always produces a decimal number. That is fine — print it
as it comes.

## Hints

- Store your working in variables:
  `total = round1 + round2 + round3`
- `/` divides: `total / 3`.
- `round(value, 2)` rounds to 2 decimal places.
- An f-string drops a variable into text: `print(f"Total: {total}")`.
""",
        "starter_code": """\
def show_rounds(round1, round2, round3):
    # 1. Add the three rounds together -> total
    # 2. Divide by 3 and round to 2 decimal places -> average
    # 3. Print two lines:
    #      Total: <total>
    #      Average: <average>
    pass  # Replace this line with your code
""",
        "solution": """\
def show_rounds(round1, round2, round3):
    total = round1 + round2 + round3
    average = round(total / 3, 2)
    print(f"Total: {total}")
    print(f"Average: {average}")
""",
        "test_code": """\
def test_uneven_rounds():
    \"\"\"prints the total and the rounded average\"\"\"
    with capture() as out:
        show_rounds(10, 12, 15)
    check_output(out.text, "Total: 37\\nAverage: 12.33")


def test_equal_rounds():
    \"\"\"an exact average still prints a decimal point\"\"\"
    with capture() as out:
        show_rounds(6, 6, 6)
    check_output(out.text, "Total: 18\\nAverage: 6.0")


def test_rounding():
    \"\"\"a long decimal is rounded to 2 places\"\"\"
    with capture() as out:
        show_rounds(5, 9, 8)
    check_output(out.text, "Total: 22\\nAverage: 7.33")


def test_zero_rounds():
    \"\"\"three zero rounds still print\"\"\"
    with capture() as out:
        show_rounds(0, 0, 0)
    check_output(out.text, "Total: 0\\nAverage: 0.0")


def test_prints_not_returns():
    \"\"\"the function prints instead of returning\"\"\"
    with capture() as out:
        result = show_rounds(10, 12, 15)
    check(result, None, name="returns None (print, don't return)")
""",
    },
    # 2 ------------------------------------------------------------------
    {
        "title": "Unpack the Dice Rolls",
        "entry_function": "turn_total",
        "problem_markdown": """\
# Unpack the Dice Rolls

Greedy Pig hands you groups of values inside a **list**, like the dice you
rolled during one turn:

```python
rolls = [3, 5, 2]
```

**Unpacking** pulls those values out into named variables in one line — much
easier to read than `rolls[0]`, `rolls[1]`, `rolls[2]` everywhere.

## The Task

Write a function `turn_total(rolls)` that receives a list of **exactly three**
dice values and **returns** their total.

## Examples

```python
turn_total([3, 5, 2])
# 10

turn_total([6, 6, 6])
# 18

turn_total([2, 3, 4])
# 9
```

## Hints

- Unpack the list into three variables:
  `first, second, third = rolls`
- Then add them up and `return` the result.
- `return` hands the value back to whoever called the function — unlike
  `print`, which only shows it on screen.
""",
        "starter_code": """\
def turn_total(rolls):
    # rolls is a list of exactly three dice values, like [3, 5, 2].
    # Unpack it into three variables, then return their total.
    pass  # Replace this line with your code
""",
        "solution": """\
def turn_total(rolls):
    first, second, third = rolls
    return first + second + third
""",
        "test_code": """\
def test_mixed_rolls():
    \"\"\"adds up three different rolls\"\"\"
    check(turn_total([3, 5, 2]), 10)


def test_all_sixes():
    \"\"\"three sixes total 18\"\"\"
    check(turn_total([6, 6, 6]), 18)


def test_small_rolls():
    \"\"\"three small rolls\"\"\"
    check(turn_total([2, 3, 4]), 9)


def test_another_list():
    \"\"\"works on any three-value list\"\"\"
    check(turn_total([4, 2, 6]), 12)


def test_returns_not_prints():
    \"\"\"the function returns a value\"\"\"
    check(turn_total([1, 1, 1]), 3, name="turn_total([1, 1, 1]) returns 3")
""",
    },
    # 3 ------------------------------------------------------------------
    {
        "title": "Rolls Plus What You Already Have",
        "entry_function": "money_if_banked",
        "problem_markdown": """\
# Rolls Plus What You Already Have

Now combine a list with other variables — and add the rule that makes Greedy
Pig dangerous.

In Greedy Pig, dice values **2 to 6** pile up in your *unbanked* pile. But a
roll of **1 wipes that pile out**. Money you had already **banked** is safe:
a 1 never touches it.

## The Task

Write a function `money_if_banked(rolls, banked)` where:

- `rolls` is a list of exactly three dice values from this turn
- `banked` is the money you had safely banked *before* the turn

Return how much money you would have **if you banked at the end of the turn**:

- If **any** of the three rolls is a `1`, this turn's rolls are lost —
  return `banked` unchanged.
- Otherwise, return `banked` plus the three rolls.

## Examples

```python
money_if_banked([3, 5, 2], 20)
# 30        (20 banked + 10 rolled)

money_if_banked([3, 1, 5], 20)
# 20        (a 1 wiped the turn — only the banked money survives)

money_if_banked([6, 6, 6], 0)
# 18        (nothing banked yet, 18 rolled)
```

## Hints

- Unpack first: `first, second, third = rolls`
- Check for the bust:
  `if first == 1 or second == 1 or third == 1:`
  (or, more neatly, `if 1 in rolls:`)
- Remember to `return` in **both** cases — the bust case and the safe case.
""",
        "starter_code": """\
def money_if_banked(rolls, banked):
    # rolls: three dice values, like [3, 5, 2]
    # banked: money that is already safe
    #
    # A roll of 1 anywhere in the list wipes this turn's rolls.
    # Otherwise the rolls are added to the banked money.
    pass  # Replace this line with your code
""",
        "solution": """\
def money_if_banked(rolls, banked):
    first, second, third = rolls
    if first == 1 or second == 1 or third == 1:
        return banked
    return banked + first + second + third
""",
        "test_code": """\
def test_safe_turn():
    \"\"\"a safe turn adds the rolls to the banked money\"\"\"
    check(money_if_banked([3, 5, 2], 20), 30)


def test_bust_in_the_middle():
    \"\"\"a 1 wipes the turn's rolls\"\"\"
    check(money_if_banked([3, 1, 5], 20), 20)


def test_nothing_banked_yet():
    \"\"\"a safe turn with nothing banked yet\"\"\"
    check(money_if_banked([6, 6, 6], 0), 18)


def test_bust_on_the_first_roll():
    \"\"\"a 1 on the first roll still wipes the turn\"\"\"
    check(money_if_banked([1, 4, 4], 12), 12)


def test_bust_on_the_last_roll():
    \"\"\"a 1 on the last roll still wipes the turn\"\"\"
    check(money_if_banked([4, 4, 1], 12), 12)


def test_another_safe_turn():
    \"\"\"banked money always survives\"\"\"
    check(money_if_banked([2, 2, 2], 55), 61)
""",
    },
    # 4 ------------------------------------------------------------------
    {
        "title": "Add Up the Scoreboard",
        "entry_function": "total_banked",
        "problem_markdown": """\
# Add Up the Scoreboard

Greedy Pig keeps the scoreboard in a **dictionary**: each player's name
(the *key*) maps to their money (the *value*).

```python
banked_money = {"Alice": 30, "Bob": 55, "Cara": 12}
```

Reading values out of a dictionary is the single most common thing an agent
does, so it starts here.

## The Task

Write a function `total_banked(banked_money)` that returns the **total money
banked by everyone** on the scoreboard.

An empty scoreboard totals `0`.

## Examples

```python
total_banked({"Alice": 30, "Bob": 55, "Cara": 12})
# 97

total_banked({"Alice": 30, "Bob": 55})
# 85

total_banked({})
# 0
```

## Hints

- `banked_money.values()` gives you just the amounts: `30, 55, 12`.
- Loop over them and add them into a running total:
  ```python
  total = 0
  for amount in banked_money.values():
      total = total + amount
  ```
- Once that works, try the one-line version: `sum(banked_money.values())`.
""",
        "starter_code": """\
def total_banked(banked_money):
    # banked_money is a dictionary like {"Alice": 30, "Bob": 55}.
    # Return the total of all the amounts.
    # An empty dictionary totals 0.
    pass  # Replace this line with your code
""",
        "solution": """\
def total_banked(banked_money):
    total = 0
    for amount in banked_money.values():
        total = total + amount
    return total
""",
        "test_code": """\
def test_three_players():
    \"\"\"adds up three players\"\"\"
    check(total_banked({"Alice": 30, "Bob": 55, "Cara": 12}), 97)


def test_two_players():
    \"\"\"adds up two players\"\"\"
    check(total_banked({"Alice": 30, "Bob": 55}), 85)


def test_empty_scoreboard():
    \"\"\"an empty scoreboard totals 0\"\"\"
    check(total_banked({}), 0)


def test_single_player():
    \"\"\"one player's total is their own money\"\"\"
    check(total_banked({"Cara": 12}), 12)


def test_eight_players():
    \"\"\"works on a full eight-player scoreboard\"\"\"
    scoreboard = {
        "Bank15": 16,
        "Bank5": 18,
        "BankRoll4": 16,
        "AdaptiveRankStop": 21,
        "StopAt21": 23,
        "MyAgent": 23,
        "StopAt20Win100": 21,
        "BankRoll3": 13,
    }
    check(total_banked(scoreboard), 151)
""",
    },
    # 5 ------------------------------------------------------------------
    {
        "title": "A Player Profile",
        "entry_function": "describe_player",
        "problem_markdown": """\
# A Player Profile

A dictionary's values do not all have to be numbers. This one mixes **text**,
**whole numbers**, a **decimal number**, and a **True/False** value:

```python
player = {
    "name": "Alice",
    "banked": 30,
    "unbanked": 8,
    "average_roll": 3.75,
    "banked_this_round": False,
}
```

You pull each one out the same way — `player["name"]`, `player["banked"]` —
but you *use* them differently.

## The Task

Write a function `describe_player(player)` that **returns** a one-line summary
string in exactly this format:

```
Alice: 38 points, avg roll 3.75, still rolling
```

Where:

- `38` is `banked + unbanked` — the player's total points
- `3.75` is the `average_roll` value, printed as it is
- the last part is `still rolling` when `banked_this_round` is `False`,
  and `done for this round` when it is `True`

## Examples

```python
describe_player({
    "name": "Alice", "banked": 30, "unbanked": 8,
    "average_roll": 3.75, "banked_this_round": False,
})
# "Alice: 38 points, avg roll 3.75, still rolling"

describe_player({
    "name": "Bob", "banked": 55, "unbanked": 0,
    "average_roll": 4.0, "banked_this_round": True,
})
# "Bob: 55 points, avg roll 4.0, done for this round"
```

## Hints

- A `True`/`False` value goes straight into an `if`:
  ```python
  if player["banked_this_round"]:
      status = "done for this round"
  else:
      status = "still rolling"
  ```
- Build the sentence with an f-string, then `return` it (do not print it):
  `return f"{name}: {total} points, avg roll {avg}, {status}"`
- Watch the commas and spaces — the tests compare the string exactly.
""",
        "starter_code": """\
def describe_player(player):
    # player has keys: "name", "banked", "unbanked",
    #                  "average_roll", "banked_this_round"
    #
    # Return a string like:
    #   Alice: 38 points, avg roll 3.75, still rolling
    #
    # banked_this_round == True  -> "done for this round"
    # banked_this_round == False -> "still rolling"
    pass  # Replace this line with your code
""",
        "solution": """\
def describe_player(player):
    name = player["name"]
    total = player["banked"] + player["unbanked"]
    avg = player["average_roll"]
    if player["banked_this_round"]:
        status = "done for this round"
    else:
        status = "still rolling"
    return f"{name}: {total} points, avg roll {avg}, {status}"
""",
        "test_code": """\
ALICE = {
    "name": "Alice",
    "banked": 30,
    "unbanked": 8,
    "average_roll": 3.75,
    "banked_this_round": False,
}

BOB = {
    "name": "Bob",
    "banked": 55,
    "unbanked": 0,
    "average_roll": 4.0,
    "banked_this_round": True,
}

CARA = {
    "name": "Cara",
    "banked": 0,
    "unbanked": 12,
    "average_roll": 4.5,
    "banked_this_round": False,
}


def test_still_rolling():
    \"\"\"a player who has not banked is still rolling\"\"\"
    check(
        describe_player(ALICE),
        "Alice: 38 points, avg roll 3.75, still rolling",
    )


def test_done_for_the_round():
    \"\"\"a player who has banked is done for the round\"\"\"
    check(
        describe_player(BOB),
        "Bob: 55 points, avg roll 4.0, done for this round",
    )


def test_nothing_banked_yet():
    \"\"\"total counts unbanked money too\"\"\"
    check(
        describe_player(CARA),
        "Cara: 12 points, avg roll 4.5, still rolling",
    )


def test_returns_the_string():
    \"\"\"the function returns the summary instead of printing it\"\"\"
    with capture() as out:
        result = describe_player(ALICE)
    check(
        result,
        "Alice: 38 points, avg roll 3.75, still rolling",
        name="returns the summary (return, don't print)",
    )
""",
    },
    # 6 ------------------------------------------------------------------
    {
        "title": "Dictionaries Inside Dictionaries",
        "entry_function": "still_rolling",
        "problem_markdown": """\
# Dictionaries Inside Dictionaries

The real game state nests things: a **list** inside a dictionary, and another
**dictionary** inside it too.

```python
state = {
    "round_no": 4,
    "players_banked_this_round": ["Bank5", "BankRoll3"],
    "banked_money": {"Bank15": 16, "Bank5": 18, "BankRoll4": 16, "BankRoll3": 13},
}
```

`state["players_banked_this_round"]` is a **list** of names — the players who
have already banked and so are out of this round. `state["banked_money"]` is a
**dictionary** holding *every* player in the game.

## The Task

Write **both** of these functions:

1. `has_banked(state, name)` — returns `True` if `name` is in the
   `players_banked_this_round` list, otherwise `False`.

2. `still_rolling(state)` — returns **how many players have not banked yet**
   this round: every player on the `banked_money` scoreboard, minus the ones
   in the `players_banked_this_round` list.

## Examples

Using the `state` above (4 players, 2 of them already banked):

```python
has_banked(state, "Bank5")
# True

has_banked(state, "Bank15")
# False

still_rolling(state)
# 2
```

## Hints

- `name in some_list` is already a `True`/`False` value — you can `return` it
  directly.
- `len(some_list)` counts the items in a list; `len(some_dict)` counts the
  keys in a dictionary.
- So the number still rolling is one `len` minus the other.
""",
        "starter_code": """\
def has_banked(state, name):
    # True if name is in state["players_banked_this_round"], else False.
    pass  # Replace this line with your code


def still_rolling(state):
    # How many players have NOT banked this round?
    # Every player in state["banked_money"], minus the ones who have banked.
    pass  # Replace this line with your code
""",
        "solution": """\
def has_banked(state, name):
    return name in state["players_banked_this_round"]


def still_rolling(state):
    total_players = len(state["banked_money"])
    banked = len(state["players_banked_this_round"])
    return total_players - banked
""",
        "test_code": """\
STATE = {
    "round_no": 4,
    "players_banked_this_round": ["Bank5", "BankRoll3"],
    "banked_money": {
        "Bank15": 16,
        "Bank5": 18,
        "BankRoll4": 16,
        "BankRoll3": 13,
    },
}

NOBODY_BANKED = {
    "round_no": 1,
    "players_banked_this_round": [],
    "banked_money": {"Bank15": 0, "Bank5": 0, "BankRoll4": 0},
}


def test_has_banked_true():
    \"\"\"has_banked: a player in the list has banked\"\"\"
    check(has_banked(STATE, "Bank5"), True, name='has_banked(state, "Bank5")')
    check(
        has_banked(STATE, "BankRoll3"),
        True,
        name='has_banked(state, "BankRoll3")',
    )


def test_has_banked_false():
    \"\"\"has_banked: a player not in the list has not banked\"\"\"
    check(
        has_banked(STATE, "Bank15"), False, name='has_banked(state, "Bank15")'
    )
    check(
        has_banked(NOBODY_BANKED, "Bank5"),
        False,
        name="nobody has banked in round 1",
    )


def test_still_rolling():
    \"\"\"still_rolling: 4 players, 2 banked, 2 still rolling\"\"\"
    check(still_rolling(STATE), 2)


def test_still_rolling_nobody_banked():
    \"\"\"still_rolling: everyone is still rolling at the start\"\"\"
    check(still_rolling(NOBODY_BANKED), 3)


def test_still_rolling_everyone_banked():
    \"\"\"still_rolling: nobody is left once everyone has banked\"\"\"
    state = {
        "round_no": 7,
        "players_banked_this_round": ["Bank15", "Bank5"],
        "banked_money": {"Bank15": 40, "Bank5": 35},
    }
    check(still_rolling(state), 0)
""",
    },
    # 7 ------------------------------------------------------------------
    {
        "title": "Read the Game State, Make a Decision",
        "entry_function": "make_decision",
        "problem_markdown": """\
# Read the Game State, Make a Decision

This is the real thing. Every roll, Greedy Pig hands your agent a
`game_state` dictionary that looks exactly like this:

```python
game_state = {
    "round_no": 4,
    "roll_no": 2,
    "players_banked_this_round": ["Bank5"],
    "banked_money": {
        "Bank15": 16, "Bank5": 18, "BankRoll4": 16, "AdaptiveRankStop": 21,
        "StopAt21": 23, "MyAgent": 23, "StopAt20Win100": 21, "BankRoll3": 13,
    },
    "unbanked_money": {
        "Bank15": 8, "Bank5": 0, "BankRoll4": 8, "AdaptiveRankStop": 8,
        "StopAt21": 8, "MyAgent": 8, "StopAt20Win100": 2, "BankRoll3": 2,
    },
}
```

Your agent answers one question, over and over: **bank, or keep rolling?**
The answer is always one of two strings: `"bank"` or `"continue"`.

Remember the rules:

- Money in `unbanked_money` is **at risk** — a roll of 1 wipes it.
- Money in `banked_money` is **safe**, and only banked money wins.
- The first player to bank **100** wins the game.

## The Task

Write a function `make_decision(game_state, my_name)` that looks up **your**
banked and unbanked money, then applies these rules **in order** and returns
the first one that fires:

1. If banking right now would take you to 100 or more
   (`my_banked + my_unbanked >= 100`) → return `"bank"` — that wins the game!
2. If your unbanked pile has reached 20 (`my_unbanked >= 20`) → return
   `"bank"` — too much to risk.
3. Otherwise → return `"continue"`.

## Examples

Using the `game_state` above, with `my_name = "MyAgent"`:

```python
make_decision(game_state, "MyAgent")
# "continue"
# MyAgent has 23 banked + 8 unbanked = 31 — nowhere near 100,
# and 8 unbanked is not risky yet.
```

If your unbanked pile were `25` instead, rule 2 would fire and the answer
would be `"bank"`.

## Hints

- Look up your own money by name:
  ```python
  my_unbanked = game_state["unbanked_money"][my_name]
  my_banked = game_state["banked_money"][my_name]
  ```
- Then it is just `if` / `elif` / `else` in the order given above.
- Return the strings exactly: `"bank"` and `"continue"` — spelling and
  lowercase matter, the game rejects anything else.

## In the real game

Your agent is a class, and `game_state` arrives the same way — the only
difference is that your name is `self.name` instead of `my_name`:

```python
class CustomPlayer(Player):
    def make_decision(self, game_state):
        my_unbanked = game_state["unbanked_money"][self.name]
        ...
```
""",
        "starter_code": """\
def make_decision(game_state, my_name):
    # Look up your own money in the game state:
    #   my_unbanked = game_state["unbanked_money"][my_name]
    #   my_banked   = game_state["banked_money"][my_name]
    #
    # Rule 1: banking now reaches 100 or more -> "bank"  (this wins!)
    # Rule 2: unbanked has reached 20         -> "bank"
    # Rule 3: otherwise                       -> "continue"
    pass  # Replace this line with your code
""",
        "solution": """\
def make_decision(game_state, my_name):
    my_unbanked = game_state["unbanked_money"][my_name]
    my_banked = game_state["banked_money"][my_name]

    if my_banked + my_unbanked >= 100:
        return "bank"
    elif my_unbanked >= 20:
        return "bank"
    else:
        return "continue"
""",
        "test_code": """\
def state(banked, unbanked, name="MyAgent"):
    \"\"\"A realistic 3-player game state with `name` holding the given money.\"\"\"
    return {
        "round_no": 4,
        "roll_no": 2,
        "players_banked_this_round": ["Bank5"],
        "banked_money": {name: banked, "Bank5": 18, "BankRoll4": 16},
        "unbanked_money": {name: unbanked, "Bank5": 0, "BankRoll4": 8},
    }


GAME_STATE = {
    "round_no": 4,
    "roll_no": 2,
    "players_banked_this_round": ["Bank5"],
    "banked_money": {
        "Bank15": 16,
        "Bank5": 18,
        "BankRoll4": 16,
        "AdaptiveRankStop": 21,
        "StopAt21": 23,
        "MyAgent": 23,
        "StopAt20Win100": 21,
        "BankRoll3": 13,
    },
    "unbanked_money": {
        "Bank15": 8,
        "Bank5": 0,
        "BankRoll4": 8,
        "AdaptiveRankStop": 8,
        "StopAt21": 8,
        "MyAgent": 8,
        "StopAt20Win100": 2,
        "BankRoll3": 2,
    },
}


def test_the_real_game_state():
    \"\"\"the worked example: 23 banked + 8 unbanked keeps rolling\"\"\"
    check(
        make_decision(GAME_STATE, "MyAgent"),
        "continue",
        name='MyAgent (23 banked, 8 unbanked) -> "continue"',
    )


def test_reads_the_right_player():
    \"\"\"the decision uses my_name, not someone else's money\"\"\"
    check(
        make_decision(GAME_STATE, "StopAt20Win100"),
        "continue",
        name='StopAt20Win100 (21 banked, 2 unbanked) -> "continue"',
    )


def test_risky_pile_banks():
    \"\"\"rule 2: 20 or more unbanked is too risky\"\"\"
    check(make_decision(state(30, 25), "MyAgent"), "bank", name="25 unbanked banks")
    check(make_decision(state(30, 20), "MyAgent"), "bank", name="exactly 20 banks")
    check(
        make_decision(state(30, 19), "MyAgent"),
        "continue",
        name="19 unbanked keeps rolling",
    )


def test_winning_move_banks():
    \"\"\"rule 1: banking now reaches 100 and wins\"\"\"
    check(
        make_decision(state(95, 5), "MyAgent"),
        "bank",
        name="95 + 5 = 100 wins the game",
    )
    check(
        make_decision(state(90, 12), "MyAgent"),
        "bank",
        name="90 + 12 = 102 wins the game",
    )


def test_rule_order():
    \"\"\"rule 1 fires even when the pile is small\"\"\"
    check(
        make_decision(state(98, 3), "MyAgent"),
        "bank",
        name="a 3-point pile still banks when it wins",
    )
""",
    },
    # 8 ------------------------------------------------------------------
    {
        "title": "What Are the Odds?",
        "entry_function": "chance_to_win_now",
        "problem_markdown": """\
# What Are the Odds?

The dice decide everything, so a good agent knows the odds. One die has six
equally likely faces:

| Face | What happens |
| --- | --- |
| 1 | **Bust** — your unbanked pile is wiped |
| 2, 3, 4, 5, 6 | That many points are added to your unbanked pile |

So the chance of busting on any single roll is `1/6`, and the chance of
surviving it is `5/6`.

**Probability = (the number of faces that give you what you want) / 6.**

## The Task

Write a function `chance_to_win_now(game_state, my_name)` that returns the
probability that the **very next roll** takes your total
(`my_banked + my_unbanked + the roll`) to **100 or more**.

Only faces `2, 3, 4, 5, 6` can do it — a `1` wipes your pile instead. So:

1. Work out your total so far: `my_banked + my_unbanked`.
2. Count how many of the faces `2, 3, 4, 5, 6` would push that total to 100
   or more.
3. Return `that count / 6`, **rounded to 2 decimal places**.

## Examples

If you have 90 banked and 6 unbanked, your total is 96. Faces 4, 5 and 6 get
you to 100 — that is 3 winning faces out of 6:

```python
chance_to_win_now(state, "MyAgent")   # 90 banked, 6 unbanked
# 0.5        (3 / 6)

chance_to_win_now(state, "MyAgent")   # 95 banked, 4 unbanked -> total 99
# 0.83       (every face from 2 to 6 wins: 5 / 6)

chance_to_win_now(state, "MyAgent")   # 60 banked, 10 unbanked -> total 70
# 0.0        (no single roll can get there)
```

## Hints

- `range(2, 7)` counts through the faces `2, 3, 4, 5, 6` (it stops *before*
  7).
- Count with a variable:
  ```python
  winning_faces = 0
  for face in range(2, 7):
      if my_total + face >= 100:
          winning_faces = winning_faces + 1
  ```
- Then `return round(winning_faces / 6, 2)`.
""",
        "starter_code": """\
def chance_to_win_now(game_state, my_name):
    # 1. Look up my banked and unbanked money, add them -> my_total
    # 2. Count the faces in 2, 3, 4, 5, 6 where my_total + face >= 100
    # 3. Return that count divided by 6, rounded to 2 decimal places
    pass  # Replace this line with your code
""",
        "solution": """\
def chance_to_win_now(game_state, my_name):
    my_total = (
        game_state["banked_money"][my_name]
        + game_state["unbanked_money"][my_name]
    )
    winning_faces = 0
    for face in range(2, 7):
        if my_total + face >= 100:
            winning_faces = winning_faces + 1
    return round(winning_faces / 6, 2)
""",
        "test_code": """\
def state(banked, unbanked, name="MyAgent"):
    \"\"\"A realistic game state with `name` holding the given money.\"\"\"
    return {
        "round_no": 9,
        "roll_no": 3,
        "players_banked_this_round": ["Bank5"],
        "banked_money": {name: banked, "Bank5": 88, "BankRoll4": 61},
        "unbanked_money": {name: unbanked, "Bank5": 0, "BankRoll4": 14},
    }


def test_three_winning_faces():
    \"\"\"96 points: faces 4, 5, 6 win -> 3/6\"\"\"
    check(chance_to_win_now(state(90, 6), "MyAgent"), 0.5)


def test_every_face_wins():
    \"\"\"99 points: every face from 2 to 6 wins -> 5/6\"\"\"
    check(chance_to_win_now(state(95, 4), "MyAgent"), 0.83)


def test_no_face_wins():
    \"\"\"70 points: no single roll can reach 100\"\"\"
    check(chance_to_win_now(state(60, 10), "MyAgent"), 0.0)


def test_only_a_six_wins():
    \"\"\"94 points: only a 6 reaches 100 -> 1/6\"\"\"
    check(chance_to_win_now(state(80, 14), "MyAgent"), 0.17)


def test_exactly_on_the_line():
    \"\"\"98 points: faces 2 to 6 all reach 100 -> 5/6\"\"\"
    check(chance_to_win_now(state(98, 0), "MyAgent"), 0.83)


def test_reads_the_right_player():
    \"\"\"the odds are worked out for my_name\"\"\"
    game_state = state(20, 3)
    check(
        chance_to_win_now(game_state, "Bank5"),
        0.0,
        name="Bank5 has 88 points: no face reaches 100",
    )
""",
    },
    # 9 ------------------------------------------------------------------
    {
        "title": "Expected Value of One Roll",
        "entry_function": "expected_change",
        "problem_markdown": """\
# Expected Value of One Roll

Odds tell you what *might* happen. **Expected value** tells you what happens
*on average* — and it is how a serious agent decides whether one more roll is
worth it.

The recipe: work out the outcome for **every** face, add them up, and divide
by 6 (because each face is equally likely).

Say your unbanked pile holds `8`:

| Face | Outcome |
| --- | --- |
| 1 | you lose the pile: **-8** |
| 2 | **+2** |
| 3 | **+3** |
| 4 | **+4** |
| 5 | **+5** |
| 6 | **+6** |

Add them: `-8 + 2 + 3 + 4 + 5 + 6 = 12`. Divide by 6: **+2.0**. On average
one more roll *gains* you 2 points, so rolling is a good bet.

## The Task

Write a function `expected_change(unbanked)` that returns the average change
to your unbanked pile from **one more roll**, rounded to 2 decimal places.

- Face `1` costs you your whole pile: `-unbanked`
- Faces `2` to `6` gain you that many points
- Add all six outcomes and divide by 6

## Examples

```python
expected_change(0)
# 3.33     (nothing to lose — rolling is almost free)

expected_change(8)
# 2.0      (still worth rolling)

expected_change(20)
# 0.0      (exactly break-even!)

expected_change(30)
# -1.67    (on average you now LOSE by rolling)
```

## The punchline

Look at those numbers. The expected value is positive below **20**, exactly
zero **at 20**, and negative above it. That is not a coincidence — it is the
mathematical reason so many strong Greedy Pig agents bank at around 20. You
just derived it.

## Hints

- Start a running total at `0`, then loop over all six faces:
  ```python
  total = 0
  for face in range(1, 7):
      if face == 1:
          total = total - unbanked
      else:
          total = total + face
  ```
- Then `return round(total / 6, 2)`.
""",
        "starter_code": """\
def expected_change(unbanked):
    # The average change to your unbanked pile from one more roll.
    #
    # Face 1      -> you lose the whole pile (-unbanked)
    # Faces 2..6  -> you gain that many points
    #
    # Add up all six outcomes, divide by 6, round to 2 decimal places.
    pass  # Replace this line with your code
""",
        "solution": """\
def expected_change(unbanked):
    total = 0
    for face in range(1, 7):
        if face == 1:
            total = total - unbanked
        else:
            total = total + face
    return round(total / 6, 2)
""",
        "test_code": """\
def test_empty_pile():
    \"\"\"with nothing to lose, a roll gains 3.33 on average\"\"\"
    check(expected_change(0), 3.33)


def test_small_pile():
    \"\"\"a pile of 8: the worked example\"\"\"
    check(expected_change(8), 2.0)


def test_break_even():
    \"\"\"a pile of 20 is exactly break-even\"\"\"
    check(expected_change(20), 0.0)


def test_losing_pile():
    \"\"\"a pile of 30 loses money on average\"\"\"
    check(expected_change(30), -1.67)


def test_below_the_line():
    \"\"\"a pile of 12 is still worth rolling\"\"\"
    check(expected_change(12), 1.33)


def test_just_over_the_line():
    \"\"\"a pile of 26 is already a losing bet\"\"\"
    check(expected_change(26), -1.0)
""",
    },
    # 10 -----------------------------------------------------------------
    {
        "title": "An Agent That Uses Expected Value",
        "entry_function": "make_decision",
        "problem_markdown": """\
# An Agent That Uses Expected Value

Time to put it together. Real agents do not cram everything into one
function — they split their thinking into **helpers**, and the decision
function calls them. Here you write the expected-value helper from the last
exercise, and a decision function that uses it on a real game state.

## The Task

Write **both** of these functions:

1. `expected_change(unbanked)` — same as the last exercise: the average change
   to your unbanked pile from one more roll, rounded to 2 decimal places.
   (Face `1` loses the pile, faces `2`–`6` gain that many points, divide by 6.)

2. `make_decision(game_state, my_name)` — looks up your own money in the game
   state, then applies these rules **in order**:
   1. If banking now reaches 100 or more (`my_banked + my_unbanked >= 100`)
      → return `"bank"`. The game is won — the odds do not matter any more.
   2. Otherwise, ask the helper. If `expected_change(my_unbanked)` is
      **greater than 0**, one more roll gains money on average → return
      `"continue"`.
   3. Otherwise the roll loses money on average → return `"bank"`.

`make_decision` must actually **call** `expected_change` — the tests check
that the two agree with each other.

## Examples

```python
# 23 banked, 8 unbanked -> expected_change(8) is +2.0, a gaining roll
make_decision(game_state, "MyAgent")
# "continue"

# 23 banked, 26 unbanked -> expected_change(26) is -1.0, a losing roll
make_decision(game_state, "MyAgent")
# "bank"

# 95 banked, 6 unbanked -> banking now reaches 101
make_decision(game_state, "MyAgent")
# "bank"
```

## Hints

- Look up your money exactly as in exercise 7:
  `game_state["unbanked_money"][my_name]`
- Rule 1 comes **first** — check the win before you check the odds.
- Then: `if expected_change(my_unbanked) > 0:` → `"continue"`, else `"bank"`.

## Taking it to the game

This *is* an agent. Drop the same two ideas into the game's `CustomPlayer` and
you have a working, mathematically-grounded strategy:

```python
from games.greedy_pig.player import Player

class CustomPlayer(Player):
    def expected_change(self, unbanked):
        total = 0
        for face in range(1, 7):
            if face == 1:
                total = total - unbanked
            else:
                total = total + face
        return round(total / 6, 2)

    def make_decision(self, game_state):
        my_unbanked = game_state["unbanked_money"][self.name]
        my_banked = game_state["banked_money"][self.name]

        if my_banked + my_unbanked >= 100:
            return "bank"
        if self.expected_change(my_unbanked) > 0:
            return "continue"
        return "bank"
```

Now go and beat it. What does this agent ignore? The round number, the other
players' scores, whether someone is one roll from winning...
""",
        "starter_code": """\
def expected_change(unbanked):
    # Face 1     -> lose the whole pile (-unbanked)
    # Faces 2..6 -> gain that many points
    # Add the six outcomes, divide by 6, round to 2 decimal places.
    pass  # Replace this line with your code


def make_decision(game_state, my_name):
    # my_unbanked = game_state["unbanked_money"][my_name]
    # my_banked   = game_state["banked_money"][my_name]
    #
    # Rule 1: banking now reaches 100 or more        -> "bank"
    # Rule 2: expected_change(my_unbanked) > 0       -> "continue"
    # Rule 3: otherwise                              -> "bank"
    pass  # Replace this line with your code
""",
        "solution": """\
def expected_change(unbanked):
    total = 0
    for face in range(1, 7):
        if face == 1:
            total = total - unbanked
        else:
            total = total + face
    return round(total / 6, 2)


def make_decision(game_state, my_name):
    my_unbanked = game_state["unbanked_money"][my_name]
    my_banked = game_state["banked_money"][my_name]

    if my_banked + my_unbanked >= 100:
        return "bank"
    if expected_change(my_unbanked) > 0:
        return "continue"
    return "bank"
""",
        "test_code": """\
def state(banked, unbanked, name="MyAgent"):
    \"\"\"A realistic game state with `name` holding the given money.\"\"\"
    return {
        "round_no": 6,
        "roll_no": 2,
        "players_banked_this_round": ["Bank5"],
        "banked_money": {name: banked, "Bank5": 48, "BankRoll4": 36},
        "unbanked_money": {name: unbanked, "Bank5": 0, "BankRoll4": 8},
    }


def test_expected_change_helper():
    \"\"\"expected_change still works\"\"\"
    check(expected_change(0), 3.33, name="expected_change(0) is 3.33")
    check(expected_change(8), 2.0, name="expected_change(8) is 2.0")
    check(expected_change(20), 0.0, name="expected_change(20) is 0.0")
    check(expected_change(30), -1.67, name="expected_change(30) is -1.67")


def test_gaining_roll_continues():
    \"\"\"a positive expected value keeps rolling\"\"\"
    check(
        make_decision(state(23, 8), "MyAgent"),
        "continue",
        name="8 unbanked (+2.0 expected) -> continue",
    )


def test_losing_roll_banks():
    \"\"\"a negative expected value banks\"\"\"
    check(
        make_decision(state(23, 26), "MyAgent"),
        "bank",
        name="26 unbanked (-1.0 expected) -> bank",
    )


def test_break_even_banks():
    \"\"\"break-even is not a gain, so it banks\"\"\"
    check(
        make_decision(state(40, 20), "MyAgent"),
        "bank",
        name="20 unbanked (0.0 expected) -> bank",
    )


def test_winning_move_beats_the_odds():
    \"\"\"rule 1: banking to reach 100 wins, whatever the odds say\"\"\"
    check(
        make_decision(state(95, 6), "MyAgent"),
        "bank",
        name="95 + 6 = 101 wins the game",
    )
    check(
        make_decision(state(97, 3), "MyAgent"),
        "bank",
        name="a small pile still banks when it wins",
    )


def test_decision_agrees_with_expected_change():
    \"\"\"make_decision follows expected_change when the game can't be won yet\"\"\"
    for unbanked in (0, 5, 12, 19, 20, 21, 26, 40):
        expected = "continue" if expected_change(unbanked) > 0 else "bank"
        check(
            make_decision(state(30, unbanked), "MyAgent"),
            expected,
            name=f"{unbanked} unbanked agrees with expected_change({unbanked})",
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
