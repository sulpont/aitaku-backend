from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import psycopg2
import os
import logging

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
        raise HTTPException(status_code=500, detail=f"DB接続エラー: {str(e)}")

# 検索条件を表すPydanticモデル
class OrderSearchCriteria(BaseModel):
    origin: str
    destination: str
    check_in_time: str
    co_passenger: int
    min_participants: int
    back_seat_passengers: int
    wants_female: bool
    id_verification_status: str
    journey_type: str
    user_id: int

# エンドポイント用のルーター
search_candidates_router = APIRouter()

# 一致する注文を検索するエンドポイント
@search_candidates_router.post("/search-orders")
def search_orders(criteria: OrderSearchCriteria):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT * FROM orders
            WHERE origin = %s
            AND destination = %s
            AND check_in_time = %s
            AND co_passenger = %s
            AND min_participants = %s
            AND back_seat_passengers = %s
            AND wants_female = %s
            AND id_verification_status = %s
            AND journey_type = %s
            AND status IN ('waiting', 'matched')
            AND user_id != %s ;
        """
        values = (
            criteria.origin,
            criteria.destination,
            criteria.check_in_time,
            criteria.co_passenger,
            criteria.min_participants,
            criteria.back_seat_passengers,
            criteria.wants_female,
            criteria.id_verification_status,
            criteria.journey_type,
            criteria.user_id
        )

        # クエリの実行
        cursor.execute(query, values)
        results = cursor.fetchall()  # リストとして結果を取得

        # 結果がない場合
        if not results:
            logger.info("emptyResult")
            return []  # 空のリストを返す

        # 一致した注文をリストとして返す
        return results  # List[dynamic]として返す
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注文検索エラー: {str(e)}")
    finally:
        cursor.close()
        conn.close()
