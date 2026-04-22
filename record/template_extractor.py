"""
record/template_extractor.py
クリック座標周辺の画像を切り出してテンプレートとして保存する
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from utils.logger import get_logger

logger = get_logger()

DEFAULT_PADDING = 30
MIN_SIZE = 16


class TemplateExtractor:
    """スクリーンショットからクリック座標周辺を切り出してテンプレート画像を保存する。"""

    def __init__(
        self,
        output_dir: Path,
        padding: int = DEFAULT_PADDING,
    ) -> None:
        self._output_dir = output_dir
        self._padding = padding
        output_dir.mkdir(parents=True, exist_ok=True)

    def extract(
        self,
        screenshot: np.ndarray,
        rel_x: int,
        rel_y: int,
        event_index: int,
    ) -> Optional[str]:
        """クリック位置周辺を切り出してPNG保存し、ファイル名を返す。

        ウィンドウ端に近い場合はパディングを自動クリップする。
        切り出しサイズが MIN_SIZE 未満になった場合は None を返す。

        Args:
            screenshot: ウィンドウ座標系の BGR 画像
            rel_x: クリックのウィンドウ相対 X 座標
            rel_y: クリックのウィンドウ相対 Y 座標
            event_index: イベント番号（ファイル名の連番に使用）

        Returns:
            保存したファイル名（例: "template_0001.png"）、失敗時は None。
        """
        h, w = screenshot.shape[:2]
        crop = self._safe_crop(screenshot, rel_x, rel_y, w, h)
        if crop is None:
            return None

        filename = f"template_{event_index:04d}.png"
        save_path = self._output_dir / filename
        if not cv2.imwrite(str(save_path), crop):
            logger.error("テンプレート保存失敗: %s", save_path)
            return None

        logger.debug(
            "テンプレート切り出し: center=(%d,%d) size=%dx%d -> %s",
            rel_x, rel_y, crop.shape[1], crop.shape[0], filename,
        )
        return filename

    def save_screenshot(
        self,
        screenshot: np.ndarray,
        event_index: int,
        output_dir: Optional[Path] = None,
    ) -> Optional[str]:
        """スクリーンショット全体を保存してファイル名を返す（デバッグ用）。

        Args:
            output_dir: 保存先ディレクトリ。省略時は self._output_dir に保存。
                        通常はテンプレートとは別のディレクトリ（記録ルート）を指定する。
        """
        save_dir = output_dir if output_dir is not None else self._output_dir
        filename = f"screen_{event_index:04d}.png"
        save_path = save_dir / filename
        if not cv2.imwrite(str(save_path), screenshot):
            logger.error("スクリーンショット保存失敗: %s", save_path)
            return None
        return filename

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    def _safe_crop(
        self,
        img: np.ndarray,
        cx: int,
        cy: int,
        img_w: int,
        img_h: int,
    ) -> Optional[np.ndarray]:
        """境界チェック付きでクリック周辺 ROI を切り出す。"""
        x1 = max(0, cx - self._padding)
        y1 = max(0, cy - self._padding)
        x2 = min(img_w, cx + self._padding)
        y2 = min(img_h, cy + self._padding)

        crop_w = x2 - x1
        crop_h = y2 - y1

        if crop_w < MIN_SIZE or crop_h < MIN_SIZE:
            logger.warning(
                "テンプレート切り出しサイズが小さすぎます: %dx%d (center=%d,%d)",
                crop_w, crop_h, cx, cy,
            )
            return None

        return img[y1:y2, x1:x2].copy()
