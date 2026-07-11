"""Seed one tutorial with one exercise about Python dictionaries.

Idempotent: rows are matched by title and updated in place, so re-running
refreshes the content without duplicating it.

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

from backend.database.db_models import Exercise, Tutorial
from backend.database.db_session import get_db_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TUTORIAL_TITLE = "Python Foundations for Agent Games"
TUTORIAL_DESCRIPTION = (
    "Short exercises covering the Python you need before writing your first "
    "game agent. Each exercise gives you a problem, starter code, and a set "
    "of test cases — submit your code to see which tests pass."
)

EXERCISE_TITLE = "Word Counter"

PROBLEM_MARKDOWN = """\
# Word Counter

Dictionaries are the workhorse of agent code: you will use them to track
scores, remember what your opponents played, and read the game state that is
passed to your agent. This exercise practises building one from scratch.

## The Task

Write a function `count_words(sentence)` that takes a string and returns a
**dictionary** mapping each word to the number of times it appears.

Words are separated by spaces. An empty string contains no words, so it
returns an empty dictionary.

## Examples

```python
count_words("the cat sat")
# {"the": 1, "cat": 1, "sat": 1}

count_words("the cat and the dog")
# {"the": 2, "cat": 1, "and": 1, "dog": 1}

count_words("")
# {}
```

## Hints

- `sentence.split()` gives you a list of the words.
- Check membership with `in`: `if word in counts:`
- Or use `counts.get(word, 0)` to read a count that might not exist yet.
"""

STARTER_CODE = """\
def count_words(sentence):
    counts = {}
    # Split the sentence into words and count each one.
    # Your code here
    return counts
"""

TEST_CASES = [
    {
        "name": "counts each word once",
        "args": ["the cat sat"],
        "expected": {"the": 1, "cat": 1, "sat": 1},
    },
    {
        "name": "counts repeated words",
        "args": ["the cat and the dog"],
        "expected": {"the": 2, "cat": 1, "and": 1, "dog": 1},
    },
    {
        "name": "a single word",
        "args": ["hello"],
        "expected": {"hello": 1},
    },
    {
        "name": "empty string has no words",
        "args": [""],
        "expected": {},
    },
]


def seed_tutorial() -> bool:
    engine = get_db_engine()
    with Session(engine) as session:
        tutorial = session.exec(
            select(Tutorial).where(Tutorial.title == TUTORIAL_TITLE)
        ).first()
        if tutorial:
            logger.info(f"Updating existing tutorial '{TUTORIAL_TITLE}'")
            tutorial.description = TUTORIAL_DESCRIPTION
        else:
            logger.info(f"Creating tutorial '{TUTORIAL_TITLE}'")
            tutorial = Tutorial(
                title=TUTORIAL_TITLE, description=TUTORIAL_DESCRIPTION
            )
        session.add(tutorial)
        session.flush()

        exercise = session.exec(
            select(Exercise)
            .where(Exercise.tutorial_id == tutorial.id)
            .where(Exercise.title == EXERCISE_TITLE)
        ).first()
        if exercise:
            logger.info(f"Updating existing exercise '{EXERCISE_TITLE}'")
        else:
            logger.info(f"Creating exercise '{EXERCISE_TITLE}'")
            exercise = Exercise(
                tutorial_id=tutorial.id,
                title=EXERCISE_TITLE,
                problem_markdown="",
                entry_function="",
                test_cases=[],
            )
        exercise.order_index = 0
        exercise.problem_markdown = PROBLEM_MARKDOWN
        exercise.starter_code = STARTER_CODE
        exercise.entry_function = "count_words"
        exercise.test_cases = TEST_CASES
        session.add(exercise)
        session.commit()

        logger.info(
            f"Seeded tutorial id={tutorial.id} with exercise id={exercise.id}"
        )
    return True


if __name__ == "__main__":
    raise SystemExit(0 if seed_tutorial() else 1)
