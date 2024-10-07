from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import psycopg2
import os
from auth import auth_router  # auth.pyからauth_routerをインポート
from search import search_router  # search.pyのルーターをインポート
from orders import order_router  # orders.pyのルーターをインポート
from search_candidates import search_candidates_router  # search_candidates.pyのルーターをインポート
from update_accept_order import update_accept_order_router, matching_router
from check_requested import check_requested_router
from send_email import send_email_router

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

# search.py用ルーターを追加
app.include_router(search_router)

# orders.py用ルーターを追加
app.include_router(order_router)

# search_candidates.py用ルーターを追加
app.include_router(search_candidates_router)

# update_accept_order.py用
app.include_router(update_accept_order_router)
app.include_router(matching_router)

# check_requested.py用
app.include_router(check_requested_router)

# send_email_router.py用
app.include_router(send_email_router)

# クラスでDB接続を管理
class Database:
    def __enter__(self):
        # コンストラクタ内でDB接続を初期化
        try:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),  # データベース名
                user=os.getenv("DB_USER"),  # ユーザー名
                password=os.getenv("DB_PASSWORD")  # パスワード
            )
            self.cursor = self.conn.cursor()
            # スキーマの設定をコンストラクタ内で行う
            self.cursor.execute("SET search_path TO public;")
            return self
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB connection error: {str(e)}")

    def __exit__(self, exc_type, exc_value, traceback):
        # リソースをクリーンアップ
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
    return {"message": "Hello Taxi!"}


# RDSへの接続テスト用エンドポイント
@app.get("/test-db-connection")
def test_db_connection():
    try:
        with Database() as db:  # DB接続をインスタンス化
            db.cursor.execute("SELECT 1;")  # データベースの接続テストクエリ
            result = db.cursor.fetchone()
            return {"message": f"DB connection successful: {result[0]}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {str(e)}")


# user_nameをトリガーにemailを取得するエンドポイント
@app.get("/get-email/{user_name}")
def get_email(user_name: str):
    try:
        with Database() as db:  # インスタンスを作成
            result = db.get_email_by_username(user_name)

        if result is None:
            raise HTTPException(status_code=404, detail="User not found")
        
        email = result[0]
        return {"user_name": user_name, "email": email}
    except Exception as e:
        print(f"Query execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Query execution error: {str(e)}")
