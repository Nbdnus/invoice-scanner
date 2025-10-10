import sys, pathlib

# ---> macht den Ordner "backend" zum Import-Pfad
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app.db import engine
from app.models import Base

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("tables created")
