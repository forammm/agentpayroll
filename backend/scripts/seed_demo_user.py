"""Create the local demo user that the frontend uses until real auth exists.

There is no authentication in the app yet (see Prompt 2-4): every API call
takes an explicit user_id. The frontend ships a fixed demo user id matching
the "Alex Parker" placeholder already shown in the sidebar UI. Run this once
against a fresh database:

    python scripts/seed_demo_user.py
"""
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.db import SessionLocal
from app.models.user import User

# Note: avoid an all-numeric-looking UUID here (e.g. one ending "...0001" with no
# a-f digits anywhere) - SQLite's NUMERIC column-type affinity silently coerces such
# a value to a plain integer on write, corrupting the primary key on read-back. This
# only affects local SQLite testing (see backend/README.md); real Postgres is unaffected
# since it has a native UUID type. Keeping at least one a-f hex digit sidesteps it.
DEMO_USER_ID = UUID("a1e5f0c2-3b7d-4a6e-9c1f-7d2b3a4c5e6f")
DEMO_USER_EMAIL = "alex@example.com"
DEMO_USER_NAME = "Alex Parker"


def seed_demo_user() -> None:
    db = SessionLocal()
    try:
        existing = db.get(User, DEMO_USER_ID)
        if existing is not None:
            print(f"Demo user already exists: {existing.id} <{existing.email}>")
            return
        user = User(id=DEMO_USER_ID, email=DEMO_USER_EMAIL, full_name=DEMO_USER_NAME)
        db.add(user)
        db.commit()
        print(f"Created demo user: {DEMO_USER_ID} <{DEMO_USER_EMAIL}>")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_user()
