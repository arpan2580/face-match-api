import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'users.db')}"
    SQLALCHEMY_DATABASE_URI = "sqlite:////app/users.db" # for containerized environment
    SQLALCHEMY_TRACK_MODIFICATIONS = False
