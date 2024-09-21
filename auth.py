from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import timedelta, datetime
from typing import Optional
import os
import psycopg2
from pydantic import BaseModel
import logging


# JWTやパスワードの設定
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ブラックリストを定義（サインアウトしたトークンを保存）
BLACKLIST = set()

auth_router = APIRouter()

# データベース接続の設定
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

# リクエストボディのモデル定義
class UserCreate(BaseModel):
    email: str
    password: str
    sex: str

# パスワードをハッシュ化する関数
def hash_password(password: str):
    return pwd_context.hash(password)

# データベースからユーザー情報を取得 (emailを使用)
def get_user_from_db(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, password, sex FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return {"email": user[0], "hashed_password": user[1], "sex": user[2]}
    return None

# データベースに新しいユーザーを作成
def create_user_in_db(password: str, email: str, sex: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    
    try:
        cursor.execute(
            """
            INSERT INTO users (password, email, sex)
            VALUES (%s, %s, %s)
            """,
            (hashed_password, email, sex),
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")
    finally:
        cursor.close()
        conn.close()

# パスワード検証
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# 認証処理 (emailで認証)
def authenticate_user(email: str, password: str):
    user = get_user_from_db(email)
    if not user:
        return False
    if not verify_password(password, user['hashed_password']):
        return False
    return user

# アクセストークンの生成
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY.encode('utf-8'), algorithm=ALGORITHM)
    # encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# トークンを無効化する関数
def add_token_to_blacklist(token: str):
    BLACKLIST.add(token)

# トークンの検証時にブラックリストをチェックする
def decode_access_token(token: str):
    if token in BLACKLIST:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

# サインインエンドポイント (emailとpasswordで認証)
@auth_router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)  # emailで認証
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが間違っています",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires  # トークンにemailを含める
    )
    return {"access_token": access_token, "token_type": "bearer"}

# アカウント作成エンドポイント
@auth_router.post("/signup")
async def create_user(user: UserCreate):
    # ユーザーが既に存在するかチェック
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (user.email,))
    existing_user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # ユーザーをデータベースに作成
    create_user_in_db(user.password, user.email, user.sex)

    return {"message": "User created successfully"}

# サインアウトエンドポイント
@auth_router.post("/signout")
async def sign_out(token: str = Depends(oauth2_scheme)):
    logging.info(f"Received token: {token}")  # ここで受信したトークンを出力
    """
    クライアントから送信されたJWTトークンを無効化
    """
    try:
        add_token_to_blacklist(token)  # トークンをブラックリストに追加
        return {"message": "サインアウトしました"}
    except Exception as e:
        logging.error(f"Signout error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="サインアウトに失敗しました")

