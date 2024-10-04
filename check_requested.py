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
check_requested_router = APIRouter()

# 注文ステータスを取得するエンドポイント
@check_requested_router.get("/check-requested/{user_id}")
def check_requested(user_id: int):

    logger.info("check-requested START")
    logger.info(user_id)
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
            SELECT * FROM orders
            WHERE user_id = %s
            AND status = 'requested';
        """
        values = (user_id,)  # タプル形式に変更

        logger.info(query)
        logger.info(values)

        cursor.execute(query, values)

        logger.info("cursor execute DONE")
        result = cursor.fetchone()

        aitaku_user_id = result[16]
        myOrderId = result[0]

        logger.info(result)

        logger.info(result[0])

        query = """
            SELECT users.user_name, users.rating, users.review_count, orders.order_id, orders.status
            FROM orders
            INNER JOIN users
            ON orders.user_id = users.user_id
            WHERE orders.user_id = %s ;
        """
        values = (result[16],)  # タプル形式に変更

        cursor.execute(query, values)

        result = cursor.fetchone()
        print('passing')
        # `result` に `myOrderId` を追加
        result = result + (myOrderId,)
        print(result)


        if result is None:
            raise HTTPException(status_code=404, detail="Order not found")

        logger.info("check-requested END")
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching order status: {str(e)}")


    finally:
        cursor.close()
        conn.close()
