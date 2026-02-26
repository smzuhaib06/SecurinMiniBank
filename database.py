from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional
from datetime import datetime


dataBaseUrl = "sqlite:///./register.db"
engine = create_engine(dataBaseUrl, echo=True)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str

class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    amount: float
    currency: str
    merchant_id: str
    idempotency_key: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

SessionLocal = lambda: Session(engine)