from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
import psycopg2
import os
import pytz
import logging
from auth import decode_access_token, oauth2_scheme  # auth.pyからoauth2_schemeをインポート

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース接続関数
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection error: {str(e)}")

# リクエストボディ用のPydanticモデル
class OrderCreate(BaseModel):
    event_id: int
    origin: str = Field(..., min_length=1, max_length=255)  # 空でない文字列、最大255文字
    destination: str = Field(..., min_length=1, max_length=255)  # 空でない文字列、最大255文字
    check_in_time: datetime
    co_passenger: int = Field(..., ge=0)  # 0以上の整数
    min_participants: int = Field(..., ge=1)  # 1以上の整数
    back_seat_passengers: int = Field(..., ge=0)  # 0以上の整数
    wants_female: bool
    id_verification_status: str = Field(..., pattern="^(verified|unverified)$")  # 'verified'または'unverified'
    journey_type: str = Field(..., pattern="^(outward|return|round_trip)$")  # 'outward', 'return', 'round_trip'
    status: str = Field(default="waiting")  # デフォルトで 'waiting'

# orders用のルーター
order_router = APIRouter()

# 新しい注文を作成するエンドポイント
@order_router.post("/orders/")
def create_order(order: OrderCreate, token: str = Depends(oauth2_scheme)):
    # トークンから user_id を取得
    try:
        user_id = decode_access_token(token)  # トークンが無効なら例外を出す
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token or user not found")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token error: {str(e)}")
    
    # データベース接続を取得
    conn = get_db_connection()
    cursor = conn.cursor()

    # 日本時間 (JST) を取得
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = datetime.now(jst)

    try:
        # 新しい注文を挿入
        cursor.execute(
            """
            INSERT INTO orders (user_id, event_id, origin, destination, check_in_time, co_passenger, min_participants, 
                                back_seat_passengers, wants_female, id_verification_status, status, journey_type, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING order_id
            """,
            (
                user_id, order.event_id, order.origin, order.destination, order.check_in_time,
                order.co_passenger, order.min_participants, order.back_seat_passengers, order.wants_female,
                order.id_verification_status, order.status, order.journey_type, now_jst, now_jst
            )
        )

        # 挿入された注文のorder_idを取得
        order_id = cursor.fetchone()[0]
        logger.info('#order_id CHECK#')
        logger.info(order_id)
        conn.commit()

        return {"order_id": order_id}

    except Exception as e:
        conn.rollback()  # エラーが発生した場合はロールバック
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")

    finally:
        cursor.close()  # カーソルを閉じる
        conn.close()  # データベース接続を閉じる

# 注文ステータスを取得するエンドポイント
@order_router.get("/orders/{order_id}")
def get_order_status(order_id: int, token: str = Depends(oauth2_scheme)):

    logger.info("get_order_status START")
    logger.info(order_id)
    ## トークンから user_id を取得
    # try:
    #     user_id = decode_access_token(token)
    #     if user_id is None:
    #         raise HTTPException(status_code=401, detail="Invalid token or user not found")
    # except Exception as e:
    #     raise HTTPException(status_code=401, detail=f"Token error: {str(e)}")

    logger.info("connection START")    
    # データベース接続を取得
    conn = get_db_connection()
    cursor = conn.cursor()
    logger.info("make cursor")    

    try:
        # 指定された注文のステータスを取得
        query = """
            SELECT users.user_name, users.rating, users.review_count
            FROM orders
            INNER JOIN users
            ON orders.user_id = users.user_id
            WHERE orders.order_id = %s ;
        """
        values = (order_id,)  # タプル形式に変更

        logger.info(query)
        logger.info(values)

        cursor.execute(query, values)
        logger.info("cursor execute DONE")
        result = cursor.fetchone()

        logger.info(result)

        if result is None:
            raise HTTPException(status_code=404, detail="Order not found")

        logger.info("get_order_status END")
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching order status: {str(e)}")


    finally:
        cursor.close()
        conn.close()
