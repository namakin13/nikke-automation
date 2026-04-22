"""
core/matcher.py
OpenCV テンプレートマッチングモジュール
画面上の特定UI要素を画像認識で検出する
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from utils.logger import get_logger

logger = get_logger()

DEFAULT_THRESHOLD = 0.80


@dataclass
class MatchResult:
    """テンプレートマッチングの結果。"""
    found: bool
    # マッチング中心座標（ウィンドウ相対）
    center_x: int = 0
    center_y: int = 0
    confidence: float = 0.0
    template_path: str = ""

    @property
    def center(self) -> tuple[int, int]:
        return (self.center_x, self.center_y)

    def __bool__(self) -> bool:
        return self.found


class TemplateMatcher:
    """テンプレートマッチングを担当するクラス。

    スクリーンショット上で指定テンプレート画像を探し、
    見つかった場合はその中心座標を返す。
    """

    def __init__(self, default_threshold: float = DEFAULT_THRESHOLD) -> None:
        self._default_threshold = default_threshold
        self._template_cache: dict[str, np.ndarray] = {}

    # ──────────────────────────────────────────
    # 公開API
    # ──────────────────────────────────────────

    def find(
        self,
        screenshot: np.ndarray,
        template_path: str | Path,
        threshold: Optional[float] = None,
        grayscale: bool = True,
    ) -> MatchResult:
        """スクリーンショット内でテンプレートを探す。

        Args:
            screenshot: 検索対象のBGR画像
            template_path: テンプレート画像のパス
            threshold: マッチング閾値（省略時はデフォルト値）
            grayscale: グレースケールで比較するか

        Returns:
            MatchResult（found=True の場合、center_x/y にウィンドウ相対座標）
        """
        thr = threshold if threshold is not None else self._default_threshold
        template = self._load_template(str(template_path))

        if template is None:
            # confidence=-1.0 でファイル未存在/読み込み失敗を閾値未満(0.0)と区別する
            return MatchResult(found=False, template_path=str(template_path), confidence=-1.0)

        if grayscale:
            src = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            tpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        else:
            src = screenshot
            tpl = template

        result = cv2.matchTemplate(src, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val < thr:
            logger.debug(
                "テンプレート不一致: %s (confidence=%.3f, threshold=%.3f)",
                Path(template_path).name,
                max_val,
                thr,
            )
            return MatchResult(
                found=False,
                confidence=max_val,
                template_path=str(template_path),
            )

        h, w = tpl.shape[:2]
        center_x = max_loc[0] + w // 2
        center_y = max_loc[1] + h // 2

        logger.debug(
            "テンプレート一致: %s (confidence=%.3f, center=(%d,%d))",
            Path(template_path).name,
            max_val,
            center_x,
            center_y,
        )

        return MatchResult(
            found=True,
            center_x=center_x,
            center_y=center_y,
            confidence=max_val,
            template_path=str(template_path),
        )

    def find_all(
        self,
        screenshot: np.ndarray,
        template_path: str | Path,
        threshold: Optional[float] = None,
        grayscale: bool = True,
    ) -> list[MatchResult]:
        """スクリーンショット内でテンプレートの全一致箇所を返す。"""
        thr = threshold if threshold is not None else self._default_threshold
        template = self._load_template(str(template_path))

        if template is None:
            return []

        if grayscale:
            src = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            tpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        else:
            src = screenshot
            tpl = template

        result = cv2.matchTemplate(src, tpl, cv2.TM_CCOEFF_NORMED)
        h, w = tpl.shape[:2]

        locations = np.where(result >= thr)
        matches: list[MatchResult] = []

        for pt in zip(*locations[::-1]):
            matches.append(
                MatchResult(
                    found=True,
                    center_x=pt[0] + w // 2,
                    center_y=pt[1] + h // 2,
                    confidence=float(result[pt[1], pt[0]]),
                    template_path=str(template_path),
                )
            )

        # 重複排除（NMS的処理）
        return self._non_max_suppress(matches, min_distance=w // 2)

    def assert_exists(
        self,
        screenshot: np.ndarray,
        template_path: str | Path,
        threshold: Optional[float] = None,
    ) -> bool:
        """指定テンプレートが画面に存在することをアサートする。

        Returns:
            存在すれば True、しなければ False（例外は投げない）。
        """
        result = self.find(screenshot, template_path, threshold)
        if not result.found:
            logger.warning(
                "ASSERT FAILED: '%s' が画面に見つかりません",
                Path(template_path).name,
            )
        return result.found

    def clear_cache(self) -> None:
        """テンプレートキャッシュをクリアする。"""
        self._template_cache.clear()

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    def _load_template(self, path: str) -> Optional[np.ndarray]:
        """テンプレート画像をキャッシュ付きで読み込む。"""
        if path in self._template_cache:
            return self._template_cache[path]

        if not Path(path).exists():
            logger.error("テンプレート画像が見つかりません: %s", path)
            return None

        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            logger.error("テンプレート画像の読み込み失敗: %s", path)
            return None

        self._template_cache[path] = img
        logger.debug("テンプレートキャッシュ登録: %s", path)
        return img

    @staticmethod
    def _non_max_suppress(
        matches: list[MatchResult],
        min_distance: int = 30,
    ) -> list[MatchResult]:
        """重複マッチングを信頼度の高いものに絞り込む（簡易NMS）。"""
        if not matches:
            return []

        sorted_matches = sorted(matches, key=lambda m: m.confidence, reverse=True)
        kept: list[MatchResult] = []

        for m in sorted_matches:
            is_duplicate = any(
                abs(m.center_x - k.center_x) < min_distance
                and abs(m.center_y - k.center_y) < min_distance
                for k in kept
            )
            if not is_duplicate:
                kept.append(m)

        return kept
