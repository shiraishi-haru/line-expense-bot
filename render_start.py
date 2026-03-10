#!/usr/bin/env python3
"""
Render 等の PaaS で PORT を環境変数から読み、uvicorn を起動する。
$PORT がシェルで展開されない環境でも確実に動く。
"""
import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
    )
