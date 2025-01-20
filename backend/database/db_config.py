import os

def get_database_url():
    if os.environ.get("TESTING") == "1":
        return "sqlite:///test.db"
    else:
        return "sqlite:///teams.db"