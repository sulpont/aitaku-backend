from fastapi import APIRouter, Query, HTTPException
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
        "event_venue_id": event[7],
        "genre_1": event[8],
        "genre_2": event[9],
        "check_in_places": event[10]  # 複数のcheck_in_placeを追加
    }

# イベント一覧を検索するエンドポイント
@search_router.get("/search-events")
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
    SELECT e.event_id, e.event_title, e.artist_name, e.open_time, e.start_time, e.prefectures, e.event_venue, c.check_in_place, e.event_venue_id, e.genre_1, e.genre_2
    FROM events e
    LEFT JOIN check_in_place c ON e.event_venue_id = c.event_venue_id
    WHERE 1=1
    """

    params = []
    
    # フリーテキスト検索
    if query:
        sql += " AND (e.event_title ILIKE %s OR e.artist_name ILIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])
    
    # ジャンルと都道府県でOR検索
    filter_clauses = []
    
    # ジャンルでの絞り込み（OR検索）
    if genre_2:
        genre_placeholders = ' OR '.join(['e.genre_2 = %s'] * len(genre_2))
        filter_clauses.append(f"({genre_placeholders})")
        params.extend(genre_2)

    # 都道府県での絞り込み（OR検索）
    if prefectures:
        processed_prefectures = [p[:-1] if p != '北海道' else p for p in prefectures]
        prefecture_placeholders = ' OR '.join(['e.prefectures = %s'] * len(processed_prefectures))
        filter_clauses.append(f"({prefecture_placeholders})")
        params.extend(processed_prefectures)

    # フィルタをORで結合
    if filter_clauses:
        sql += " AND (" + " OR ".join(filter_clauses) + ")"

    # 日付範囲フィルタリング
    if start_time and end_time:
        sql += " AND e.start_time BETWEEN %s AND %s"
        params.extend([f"{start_time} 00:00:00", f"{end_time} 23:59:59"])
    elif start_time:
        sql += " AND e.start_time >= %s"
        params.append(f"{start_time} 00:00:00")
    elif end_time:
        sql += " AND e.start_time <= %s"
        params.append(f"{end_time} 23:59:59")

    # クエリ実行
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()

    # 各イベントを整形して、datetime を文字列形式に変換
    events = [serialize_event(row) for row in rows]

    cursor.close()
    conn.close()

    # 整形されたデータをJSONとして返す
    return JSONResponse(content={"events": events}, media_type="application/json; charset=utf-8")

# 特定のイベントを取得するエンドポイント
@search_router.get("/events/{event_id}")
def get_event(event_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    # イベント取得クエリ
    sql_event = """
    SELECT e.event_id, e.event_title, e.artist_name, e.open_time, e.start_time, e.prefectures, e.event_venue, e.event_venue_id, e.genre_1, e.genre_2
    FROM events e
    WHERE e.event_id = %s
    """
    
    cursor.execute(sql_event, (event_id,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Event not found")
    
    # 複数のcheck_in_placeを取得するクエリ
    sql_check_in_places = """
    SELECT check_in_place
    FROM check_in_place
    WHERE event_venue_id = %s
    """
    
    cursor.execute(sql_check_in_places, (event[7],))  # event_venue_idを使ってクエリ
    check_in_places = cursor.fetchall()

    # check_in_placeをリストとして格納
    check_in_place_list = [place[0] for place in check_in_places]

    # イベントデータにcheck_in_placeを追加して整形
    event_data = list(event) + [check_in_place_list]

    cursor.close()
    conn.close()

    return JSONResponse(content=serialize_event(event_data), media_type="application/json; charset=utf-8")
