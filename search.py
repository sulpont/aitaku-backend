from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import psycopg2
import os
from datetime import datetime
from typing import Optional, List

search_router = APIRouter()

# データベース接続の設定
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

# datetimeオブジェクトをシリアライズ可能な形式に変換
def serialize_event(event):
    return {
        "event_id": event[0],
        "event_title": event[1],
        "artist_name": event[2],
        "open_time": event[3].strftime('%Y-%m-%d %H:%M:%S') if isinstance(event[3], datetime) else event[3],
        "start_time": event[4].strftime('%Y-%m-%d %H:%M:%S') if isinstance(event[4], datetime) else event[4],
        "prefectures": event[5],
        "event_venue": event[6],
        "genre_1": event[7],
        "genre_2": event[8]
    }

@search_router.get("/search-events")  # 末尾にスラッシュを付けない
def search_events(
    query: Optional[str] = Query(None),
    genre_2: Optional[List[str]] = Query(None),  # 複数ジャンルの絞り込み
    prefectures: Optional[List[str]] = Query(None),  # 複数都道府県の絞り込み
    start_time: Optional[str] = Query(None),  # 公演日の開始
    end_time: Optional[str] = Query(None)  # 公演日の終了
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 基本的なクエリ構造
    sql = """
    SELECT event_id, event_title, artist_name, open_time, start_time, prefectures, event_venue, genre_1, genre_2
    FROM events
    WHERE 1=1
    """

    params = []
    
    # フリーテキスト検索
    if query:
        sql += " AND (event_title ILIKE %s OR artist_name ILIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])
    
    # ジャンルと都道府県でOR検索
    filter_clauses = []
    
    # ジャンルでの絞り込み（OR検索）
    if genre_2:
        genre_placeholders = ' OR '.join(['genre_2 = %s'] * len(genre_2))
        filter_clauses.append(f"({genre_placeholders})")
        params.extend(genre_2)

    # 都道府県での絞り込み（OR検索）
    if prefectures:
        prefecture_placeholders = ' OR '.join(['prefectures = %s'] * len(prefectures))
        filter_clauses.append(f"({prefecture_placeholders})")
        params.extend(prefectures)

    # フィルタをORで結合
    if filter_clauses:
        sql += " AND (" + " OR ".join(filter_clauses) + ")"

    ## よくある ##
    start_time = f"{start_time} 00:00:00"
    end_time = f"{end_time} 23:59:59"

    # 公演日の期間での絞り込み（start_timeとend_timeの間にあるイベント）
    if start_time and end_time:
        sql += " AND start_time BETWEEN %s AND %s"
        params.extend([start_time, end_time])
    elif start_time:  # 開始日だけ指定された場合
        sql += " AND start_time >= %s"
        params.append(start_time)
    elif end_time:  # 終了日だけ指定された場合
        sql += " AND start_time <= %s"
        print(sql)
        params.append(end_time)

    # クエリ実行
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()

    # 各イベントを整形して、datetime を文字列形式に変換
    events = [serialize_event(row) for row in rows]

    cursor.close()
    conn.close()

    # 整形されたデータをJSONとして返す
    return JSONResponse(content={"events": events}, media_type="application/json; charset=utf-8")
