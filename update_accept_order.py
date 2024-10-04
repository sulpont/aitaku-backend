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
    order_id: int
    my_order_id: int

# エンドポイント用のルーター
update_accept_order_router = APIRouter()
matching_router = APIRouter()

# 一致する注文を検索するエンドポイント
@update_accept_order_router.post("/update-accept-order")
def update_accept_order(criteria: OrderSearchCriteria):
    logger.info("update-accept-order")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT user_id
            FROM orders
            WHERE order_id = %s;
        """
        values = (criteria.order_id,)  # タプルとして渡す

        logger.info(query)
        logger.info(values)

        # クエリの実行
        cursor.execute(query, values)
        aitaku_user_id = cursor.fetchone()

        query = """
            SELECT user_id
            FROM orders
            WHERE order_id = %s;
        """
        values = (criteria.my_order_id,)  # タプルとして渡す

        logger.info(query)
        logger.info(values)

        # クエリの実行
        cursor.execute(query, values)
        myUserId = cursor.fetchone()

        # 指定された注文のステータスを更新するSQLクエリ
        query = """
            UPDATE public.orders
            SET status='requested', aitaku_user_id = %s
            WHERE order_id = %s;
        """
        values = (myUserId, criteria.order_id,)  # タプルとして渡す

        logger.info(query)
        logger.info(values)

        # クエリの実行
        cursor.execute(query, values)

        query = """
            UPDATE public.orders
            SET status='approved_wating', aitaku_user_id = %s
            WHERE order_id = %s;
        """
        values = (aitaku_user_id, criteria.my_order_id,)  # タプルとして渡す

        logger.info(query)
        logger.info(values)

        # クエリの実行
        cursor.execute(query, values)
        conn.commit()  # 変更をデータベースに保存

        return {"message": "注文が正常に更新されました。"}

    except Exception as e:
        conn.rollback()  # エラーが発生した場合はロールバック
        raise HTTPException(status_code=500, detail=f"注文検索エラー: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()

# 両ユーザーをマッチングするエンドポイント
@matching_router.post("/matching")
def matching_order(criteria: OrderSearchCriteria):
    logger.info("matching")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 指定された注文のステータスを更新するSQLクエリ
        query = """
            UPDATE public.orders
            SET status='matched'
            WHERE order_id = %s;
        """
        values = (criteria.order_id,)  # タプルとして渡す

        logger.info(query)
        logger.info(values)

        # クエリの実行
        cursor.execute(query, values)

        query = """
            UPDATE public.orders
            SET status='matched'
            WHERE order_id = %s;
        """
        values = (criteria.my_order_id,)  # タプルとして渡す

        logger.info(query)
        logger.info(values)

        # クエリの実行
        cursor.execute(query, values)
        conn.commit()  # 変更をデータベースに保存

        return {"order_id": criteria.order_id, "my_order_id": criteria.my_order_id}
        # return {"message": "注文が正常に更新されました。"}

    except Exception as e:
        conn.rollback()  # エラーが発生した場合はロールバック
        raise HTTPException(status_code=500, detail=f"注文検索エラー: {str(e)}")
    
    finally:
        cursor.close()
        conn.close()