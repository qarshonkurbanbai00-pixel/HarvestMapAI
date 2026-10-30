import argparse
import getpass
from sqlalchemy import select
from app.database import SessionLocal
from app.models import User
from app.security import password_hash
from pydantic import TypeAdapter, EmailStr

parser = argparse.ArgumentParser(description="Create an administrator; password is prompted, never hard-coded.")
parser.add_argument("--email", required=True)
parser.add_argument("--name", default="Әкімші")
args = parser.parse_args()
email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
password = getpass.getpass("New admin password (at least 12 characters): ")
if len(password) < 12:
    raise SystemExit("Password must have at least 12 characters.")
if password != getpass.getpass("Confirm password: "):
    raise SystemExit("Passwords differ.")
with SessionLocal() as db:
    if db.scalar(select(User).where(User.email == email)):
        raise SystemExit("Email exists. Use the admin dashboard to manage roles.")
    db.add(User(email=email, name=args.name, role="admin", password_hash=password_hash.hash(password)))
    db.commit()
print("Administrator created.")
