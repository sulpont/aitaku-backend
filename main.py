from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import psycopg2
import os
from auth import auth_router  # auth.pyからauth_routerをインポート

load_dotenv()

app = FastAPI()

# CORSミドルウェアの追加
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 全てのオリジンからのアクセスを許可
    allow_credentials=True,
    allow_methods=["*"],  # 全てのHTTPメソッドを許可
    allow_headers=["*"],  # 全てのヘッダーを許可
)

# auth.pyからルーターを追加
app.include_router(auth_router)

# クラスでDB接続を管理
class Database:
    def __init__(self):
        # コンストラクタ内でDB接続を初期化
        try:
            self.conn = psycopg2.connect(
                host=os.environ.get("DB_HOST"),
                database=os.environ.get("DB_NAME"),  # データベース名
                user=os.environ.get("DB_USER"),  # ユーザー名
                password=os.environ.get("DB_PASSWORD")  # パスワード
            )
            self.cursor = self.conn.cursor()
            # スキーマの設定をコンストラクタ内で行う
            self.cursor.execute("SET search_path TO public;")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB connection error: {str(e)}")

    def close(self):
        self.cursor.close()
        self.conn.close()

    def get_email_by_username(self, user_name: str):
        # クエリを実行し、結果を返すメソッド
        try:
            self.cursor.execute("SELECT email FROM test WHERE user_name = %s", (user_name,))
            return self.cursor.fetchone()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")


# ルートエンドポイント: "Hello Taxi"メッセージを表示
@app.get("/")
def read_root():
    return {"message": "Hello Taxi...!"}


# RDSへの接続テスト用エンドポイント
@app.get("/test-db-connection")
def test_db_connection():
    try:
        db = Database()  # DB接続をインスタンス化
        db.cursor.execute("SELECT 1;")  # データベースの接続テストクエリ
        result = db.cursor.fetchone()
        db.close()
        return {"message": f"DB connection successful: {result[0]}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {str(e)}")


# user_nameをトリガーにemailを取得するエンドポイント
@app.get("/get-email/{user_name}")
def get_email(user_name: str):
    try:
        db = Database()  # インスタンスを作成
        result = db.get_email_by_username(user_name)
        db.close()

        if result is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        email = result[0]
        return {"user_name": user_name, "email": email}
    except Exception as e:
        print(f"Query execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")
