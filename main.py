from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import SessionLocal, engine, SQLModel, User, Transaction
from pydantic import BaseModel, EmailStr
import bcrypt
from jose import JWTError, jwt  # type: ignore
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import asynccontextmanager
from sqlmodel import select
import logging



security = HTTPBearer()
SECRET_KEY = "qwert"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10

login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_TIME = 300

logging.basicConfig(filename='security.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def create_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            logging.warning(f"Invalid token: missing user_id")
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        logging.warning(f"Invalid token: JWT decode failed")
        raise HTTPException(status_code=401, detail="Invalid token")

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PaymentRequest(BaseModel):
    amount: float
    currency: str
    merchant_id: str
    idempotency_key: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
@app.post("/register")
def register_user(user: UserCreate):
    with SessionLocal() as session:
        existing_user = session.exec(select(User).where(User.email == user.email)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        new_user = User(email=user.email, hashed_password=bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode())
        session.add(new_user)
        session.commit()
        session.refresh(new_user)
        return {"message": "User registered successfully", "user_id": new_user.id}    

@app.post("/login")
def login_user(user: UserLogin):
    email = user.email
    now = datetime.utcnow()
    
    login_attempts[email] = [t for t in login_attempts[email] if (now - t).total_seconds() < LOCKOUT_TIME]
    
    if len(login_attempts[email]) >= MAX_LOGIN_ATTEMPTS:
        logging.warning(f"Rate limit exceeded for email: {email}")
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later")
    
    with SessionLocal() as session:
        db_user = session.exec(select(User).where(User.email == email)).first()
        if not db_user or not bcrypt.checkpw(user.password.encode(), db_user.hashed_password.encode()):
            login_attempts[email].append(now)
            logging.warning(f"Failed login attempt for email: {email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        login_attempts[email].clear()
        if db_user.id is None:
            raise HTTPException(status_code=500, detail="User ID not found")
        token = create_token(db_user.id)
        return {"access_token": token, "token_type": "bearer"}

@app.post("/payment")
def process_payment(payment: PaymentRequest, user_id: int = Depends(verify_token)):
    with SessionLocal() as session:
        existing = session.exec(select(Transaction).where(
            Transaction.idempotency_key == payment.idempotency_key
        )).first()
        if existing:
            logging.warning(f"Duplicate payment attempt by user {user_id}: {payment.idempotency_key}")
            raise HTTPException(status_code=400, detail="Duplicate payment detected")
        
        if payment.amount <= 0:
            logging.warning(f"Invalid payment amount by user {user_id}: {payment.amount}")
            raise HTTPException(status_code=400, detail="Invalid amount")
        
        transaction = Transaction(
            user_id=user_id,
            amount=payment.amount,
            currency=payment.currency,
            merchant_id=payment.merchant_id,
            idempotency_key=payment.idempotency_key
        )
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return {"message": "Payment processed", "transaction_id": transaction.id}

@app.get("/transactions")
def get_transactions(user_id: int = Depends(verify_token)):
    with SessionLocal() as session:
        transactions = session.exec(select(Transaction).where(Transaction.user_id == user_id)).all()
        return {"transactions": transactions}

app.mount("/static", StaticFiles(directory="static"), name="static")














# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )  