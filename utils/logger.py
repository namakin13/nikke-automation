"""
utils/logger.py
ロギングユーティリティ
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from pathlib import Path

_setup_lock = threading.Lock()


def setup_logger(
    name: str = "nikke_auto",
    level: str = "INFO",
    log_dir: str = "logs",
    screenshot_on_error: bool = True,
) -> logging.Logger:
    """アプリケーションロガーを初期化して返す。"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    log_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    with _setup_lock:
        if logger.handlers:
            return logger

        # フォーマット
        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # コンソールハンドラ
        ch = logging.StreamHandler()
        ch.setLevel(log_level)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

        # ファイルハンドラ（日付ごと）
        log_file = Path(log_dir) / f"{datetime.now().strftime('%Y%m%d')}.log"
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(log_level)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def get_logger(name: str = "nikke_auto") -> logging.Logger:
    """既存ロガーを取得する。"""
    return logging.getLogger(name)
