import warnings

from passlib.utils.compat import suppress_cause
from passlib.utils.decor import memoized_property

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning, message=".*error reading bcrypt version.*")
    from passlib.handlers.bcrypt import bcrypt