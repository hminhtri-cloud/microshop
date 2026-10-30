from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import User
from app.schemas import UserRegister, UserResponse, UserLogin, TokenResponse
from app.dependencies import get_current_user
from app.security import password_context, DUMMY_HASH, create_access_token

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)

def register(    user_data: UserRegister, db: Session = Depends(get_db)):
    existing_email= (
        db.query(User).filter(User.email == user_data.email).first()
    )

    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    existing_username = (
        db.query(User).filter(User.username == user_data.username).first()
    )

    if existing_username:
        raise HTTPException(
            status_code=409,
            detail="Username already taken"
        )

    hashed_password = password_context.hash(user_data.password)

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        role="customer"
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username or email already registered") from None
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(user_data.email)).first()
    password_hash = user.hashed_password if user else DUMMY_HASH
    valid_password = password_context.verify(user_data.password, password_hash)
    if user is None or not valid_password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserResponse)
def current_user(user: User = Depends(get_current_user)):
    return user
