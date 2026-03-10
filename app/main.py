"""
FastAPI アプリケーション。
LINE Webhook 受信・署名検証・ルーティング。
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, PostbackEvent
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db, init_db
from app.line_handlers.webhook_handler import handle_webhook_events

logger = logging.getLogger(__name__)


def _get_line_bot():
    settings = get_settings()
    return LineBotApi(settings.line_channel_access_token)


def _get_parser():
    settings = get_settings()
    return WebhookParser(settings.line_channel_secret)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時にDB初期化。"""
    init_db()
    yield


app = FastAPI(
    title="LINE交通費精算Bot",
    description="身内向け交通費精算をLINEで行うBotのWebhookサーバー",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"status": "ok", "message": "LINE交通費精算Bot Webhook"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """
    LINE Platform から呼ばれる Webhook エンドポイント。
    署名検証のうえ、メッセージ・ポストバックを処理する。
    """
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    if not signature:
        logger.warning("Webhook: Missing X-Line-Signature header")
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature")

    parser = _get_parser()
    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        logger.warning(
            "Webhook: Invalid signature. Check that LINE_CHANNEL_SECRET in .env "
            "matches the Channel secret in LINE Developers."
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    target_events = [ev for ev in events if isinstance(ev, (MessageEvent, PostbackEvent))]
    if target_events:
        line_bot_api = _get_line_bot()
        handle_webhook_events(line_bot_api, target_events, db)

    return {"status": "ok"}
