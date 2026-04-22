"""
record/player.py
記録済み操作の再生エンジン

再生戦略:
  1. テンプレートマッチングで要素を探してクリック（位置が多少ずれても対応）
  2. マッチしない場合は記録時のウィンドウ相対座標にフォールバック
     （ウィンドウサイズが変わっていれば座標をスケール補正）
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.capture import ScreenCapture
from core.controller import GameController
from core.matcher import TemplateMatcher
from core.window import GameWindow
from record.models import ClickEvent, KeyEvent, Recording
from utils.logger import get_logger

logger = get_logger()


@dataclass
class PlayResult:
    """再生結果サマリー。"""
    total_events: int = 0
    played: int = 0
    fallback_count: int = 0   # テンプレート不一致で座標フォールバックした回数
    failed_count: int = 0     # クリック/キー操作失敗回数
    elapsed: float = 0.0


class EventPlayer:
    """recording.json を読み込んでイベントを再生する。"""

    def __init__(
        self,
        name: str,
        window: GameWindow,
        capture: ScreenCapture,
        matcher: TemplateMatcher,
        controller: GameController,
        recordings_base: Path,
        speed: float = 1.0,
        settings: dict | None = None,
    ) -> None:
        self._name = name
        self._window = window
        self._capture = capture
        self._matcher = matcher
        self._controller = controller
        self._recordings_base = recordings_base
        self._speed = max(speed, 0.1)  # 0 除算防止
        self._settings = settings or {}

        pb_cfg = self._settings.get("playback", {})
        self._allow_fallback = pb_cfg.get("allow_fallback", True)
        self._scale_coords = pb_cfg.get("scale_coords", True)
        raw_thr = pb_cfg.get("template_threshold", None)
        self._threshold: Optional[float] = float(raw_thr) if raw_thr is not None else None

    # ──────────────────────────────────────────
    # 公開API
    # ──────────────────────────────────────────

    def play(self) -> PlayResult:
        """全イベントを順に再生する。"""
        recording_dir = self._recordings_base / self._name
        json_path = recording_dir / "recording.json"

        if not json_path.exists():
            logger.error("recording.json が見つかりません: %s", json_path)
            return PlayResult()

        try:
            with json_path.open(encoding="utf-8") as f:
                recording = Recording.from_dict(json.load(f))
        except Exception as exc:  # noqa: BLE001
            logger.exception("recording.json の読み込みに失敗しました: %s", json_path)
            return PlayResult()

        logger.info("=" * 50)
        logger.info("再生モード開始: '%s'", self._name)
        logger.info("  イベント数: %d", len(recording.events))
        logger.info("  再生速度: %.1fx", self._speed)
        logger.info("  記録時ウィンドウサイズ: %dx%d",
                    recording.meta.window_width, recording.meta.window_height)
        logger.info("=" * 50)

        if not recording.events:
            logger.warning("イベントが 0 件です。記録時にウィンドウ外をクリックしていた可能性があります。")
            return PlayResult()

        # ── 再生前にゲームウィンドウをフォーカス ──
        logger.info("ゲームウィンドウをフォーカスします...")
        focused = self._window.focus()
        if not focused:
            logger.warning("ウィンドウのフォーカスに失敗しました。クリックが意図しない場所に当たる可能性があります。")
        time.sleep(2.0)  # フォーカス後の画面遷移待機

        result = PlayResult(total_events=len(recording.events))
        start_time = time.time()
        prev_ts = 0.0

        for event in recording.events:
            self._wait_interval(event.timestamp, prev_ts)
            prev_ts = event.timestamp

            if isinstance(event, ClickEvent):
                ok, used_fallback = self._play_click(event, recording)
                if ok:
                    result.played += 1
                    if used_fallback:
                        result.fallback_count += 1
                else:
                    result.failed_count += 1

            elif isinstance(event, KeyEvent):
                ok = self._play_key(event)
                if ok:
                    result.played += 1
                else:
                    result.failed_count += 1

        result.elapsed = round(time.time() - start_time, 3)

        logger.info("─" * 40)
        logger.info(
            "再生完了: %d/%d イベント | フォールバック: %d | 失敗: %d | 経過: %.1fs",
            result.played, result.total_events,
            result.fallback_count, result.failed_count, result.elapsed,
        )
        return result

    # ──────────────────────────────────────────
    # イベント再生
    # ──────────────────────────────────────────

    def _play_click(self, event: ClickEvent, recording: Recording) -> tuple[bool, bool]:
        """クリックイベントを再生する。

        Returns:
            (成功フラグ, フォールバック使用フラグ)
        """
        template_path = self._resolve_template_path(event, recording)
        used_fallback = False

        # ── テンプレートマッチングを試みる ──
        if template_path is not None and template_path.exists():
            screenshot = self._capture.capture()
            if screenshot is not None:
                match = self._matcher.find(
                    screenshot, template_path, threshold=self._threshold
                )
                if match.found:
                    logger.info(
                        "[再生] クリック (テンプレート一致): center=(%d,%d) conf=%.3f",
                        match.center_x, match.center_y, match.confidence,
                    )
                    ok = self._controller.click_match(match, delay=0.0)
                    return ok, False
                else:
                    logger.debug(
                        "[再生] テンプレート不一致 (conf=%.3f): %s",
                        match.confidence, template_path.name,
                    )
        else:
            if template_path is not None:
                logger.debug("[再生] テンプレートファイルなし: %s", event.template_file)

        # ── フォールバック: ウィンドウ相対座標でクリック ──
        if not self._allow_fallback:
            logger.warning("[再生] テンプレート不一致かつフォールバック無効のためスキップ")
            return False, False

        rel_x, rel_y = self._scale_point(
            event.rel_x, event.rel_y, recording
        )
        logger.info(
            "[再生] クリック (座標フォールバック): rel=(%d,%d)",
            rel_x, rel_y,
        )
        ok = self._controller.click(rel_x, rel_y, delay=0.0, button=event.button)
        used_fallback = True
        return ok, used_fallback

    def _play_key(self, event: KeyEvent) -> bool:
        logger.info("[再生] キー: %s", event.key)
        return self._controller.press_key(event.key, delay=0.0)

    # ──────────────────────────────────────────
    # ユーティリティ
    # ──────────────────────────────────────────

    def _wait_interval(self, current_ts: float, prev_ts: float) -> None:
        """イベント間の待機（speed 倍率を適用）。最大 30s にキャップ。"""
        duration = (current_ts - prev_ts) / self._speed
        duration = min(duration, 30.0)
        if duration > 0.05:
            time.sleep(duration)

    def _resolve_template_path(
        self, event: ClickEvent, recording: Recording
    ) -> Optional[Path]:
        """テンプレートファイル名 → 絶対パスに変換する。"""
        if not event.template_file:
            return None
        return self._recordings_base / recording.meta.name / "templates" / event.template_file

    def _scale_point(
        self, rel_x: int, rel_y: int, recording: Recording
    ) -> tuple[int, int]:
        """記録時と再生時のウィンドウサイズが異なる場合に座標をスケール補正する。"""
        if not self._scale_coords:
            return rel_x, rel_y

        rec_w = recording.meta.window_width
        rec_h = recording.meta.window_height
        if rec_w <= 0 or rec_h <= 0:
            return rel_x, rel_y

        rect = self._window.get_rect()
        if rect is None:
            return rel_x, rel_y

        cur_w = rect.width
        cur_h = rect.height
        if cur_w == rec_w and cur_h == rec_h:
            return rel_x, rel_y

        scaled_x = int(rel_x * cur_w / rec_w)
        scaled_y = int(rel_y * cur_h / rec_h)
        logger.debug(
            "座標スケール補正: (%d,%d) → (%d,%d) [%dx%d → %dx%d]",
            rel_x, rel_y, scaled_x, scaled_y, rec_w, rec_h, cur_w, cur_h,
        )
        return scaled_x, scaled_y
