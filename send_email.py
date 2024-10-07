from fastapi import APIRouter, HTTPException
import psycopg2
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# データベース接続関数
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )
    return conn

# メール送信関数
def send_email(to_email, subject, body):

    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT'))
    GMAIL_USERNAME = os.getenv('GMAIL_USERNAME')
    GMAIL_PASSWORD = os.getenv('GMAIL_PASSWORD')

    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_USERNAME, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USERNAME, to_email, msg.as_string())
        server.quit()

        logger.info(f"Email sent to {to_email}")  # メール送信成功のログ出力

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")  # エラーログ出力
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

# ルーター作成
send_email_router = APIRouter()

@send_email_router.post("/send-confirmation-email/{order_id}")
def send_confirmation_email(order_id: int):
    logger.info("### send_confirmation_email START ###")  # メール送信関数の開始をログ出力

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # order_idを使ってuser_idとaitaku_user_idのメールアドレスを取得
        query = """
            SELECT u.email AS user_email, a.email AS aitaku_email
            FROM orders
            JOIN users AS u ON orders.user_id = u.user_id
            JOIN users AS a ON orders.aitaku_user_id = a.user_id
            WHERE orders.order_id = %s;
        """
        cursor.execute(query, (order_id,))
        result = cursor.fetchone()

        if result is None:
            raise HTTPException(status_code=404, detail="Order not found")

        user_email = result[0]
        aitaku_email = result[1]

        # メールの件名と本文を設定
        subject = '[あいタク] 予約が確定しました'

        # 1. ユーザー宛に送信するメール (To: user_email)
        body_for_user = f'あいタク相手のEメールアドレスは {aitaku_email} です。'
        logger.info(f"Sending confirmation email to user: {user_email}")
        send_email(user_email, subject, body_for_user)
        logger.info("Confirmation email sent to user.")

        # 2. 相手（あいタク相手）宛に送信するメール (To: aitaku_email)
        body_for_aitaku = f'あいタク相手のEメールアドレスは {user_email} です。'
        logger.info(f"Sending confirmation email to aitaku: {aitaku_email}")
        send_email(aitaku_email, subject, body_for_aitaku)
        logger.info("Confirmation email sent to aitaku.")

        return {"message": "Emails sent successfully"}

    except Exception as e:
        logger.error(f"Error: {str(e)}")  # エラーログ出力
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

    finally:
        cursor.close()
        conn.close()
