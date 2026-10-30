"""Run interactively: docker compose exec auth-service python -m app.create_admin."""
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import User
from app.schemas import UserRegister
from app.security import password_context


def create_admin(db, data: UserRegister):
    existing = db.query(User).filter(or_(User.username == data.username, User.email == str(data.email))).first()
    if existing:
        raise ValueError("Username or email already exists; existing accounts will not be modified")
    user = User(
        username=data.username, email=str(data.email),
        hashed_password=password_context.hash(data.password), role="admin",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Username or email already exists") from None
    db.refresh(user)
    return user


def main():
    try:
        username = input("Admin username: ").strip()
        email = input("Admin email: ").strip()
        password = getpass("Admin password: ")
        if password != getpass("Confirm password: "):
            raise ValueError("Passwords do not match")
        data = UserRegister(username=username, email=email, password=password)
        with SessionLocal() as db:
            user = create_admin(db, data)
            print(f"Created admin account: {user.username} (id={user.id})")
    except ValidationError as error:
        # Pydantic's default string includes input values, potentially passwords.
        for item in error.errors(include_input=False, include_context=False):
            print(f"{'.'.join(map(str, item['loc']))}: {item['msg']}")
        raise SystemExit(1)
    except ValueError as error:
        print(str(error))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
