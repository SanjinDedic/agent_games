import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
CURRENT_DIR = os.path.dirname(__file__)
CURRENT_DB = os.path.join(CURRENT_DIR, "teams.db")