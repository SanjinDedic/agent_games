import os
from sqlmodel import SQLModel, create_engine
from config import CURRENT_DB

def reset_database(test_db=None):
    if test_db is None:
        test_db = "test_db.db"
    
    # Copy the current database file to the test database file
    os.system(f"cp {CURRENT_DB} {test_db}")
    
    engine = create_engine(f'sqlite:///{test_db}')
    
    # Drop all tables
    SQLModel.metadata.drop_all(bind=engine)
    
    # Create all tables
    SQLModel.metadata.create_all(bind=engine)
    
    return test_db

new_db = reset_database()