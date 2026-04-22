"""
record/recorder.py
操作記録エンジン

pynput のリスナーをバックグラウンドスレッドで起動し、
マウスクリックとキーボードイベントを記録する。

スレッド設計:
  [pynput コールバック (別スレッド)] → queue.Queue → [メインスレッド: キャプチャ・保存]
  mss によるキャプチャはスレッドセーフでないため、コールバック内では行わない。
"""
from __future__ import annotations

import json
import queue
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pynput import keyboard, mouse

from core.capture import ScreenCapture
from core.window import GameWindow
from record.models import ClickEvent, KeyEvent, Recording, RecordingMeta, pynput_key_to_str
from record.template_extractor import TemplateExtractor
from utils.logger import get_logger

logger = get_logger()

# デフォルト停止キー
DEFAULT_STOP_KEY = "f9"


@dataclass
class _RawClickEvent:
    """コールバックスレッドからキューに積む生イベント。"""
    timestamp: float
    abs_x: int
    abs_y: int
    button: str


@dataclass
class _RawKeyEvent:
    timestamp: float
    key_str: str
    action: str  # "press" or "release"


class EventRecorder:
    """マウス・キーボードイベントを記録する。

    使い方:
        recorder = EventRecorder(name, window, capture, extractor, output_dir, settings)
        recording = recorder.start()   # ブロッキング。停止キーで終了
        # → Recording オブジェクトが返る
    """

    def __init__(
        self,
        name: str,
        window: GameWindow,
        capture: ScreenCapture,
        extractor: TemplateExtractor,
        output_dir: Path,
        settings: dict,
    ) -> None:
        self._name = name
        self._window = window
        self._capture = capture
        self._extractor = extractor
        self._output_dir = output_dir
        self._settings = settings

        rec_cfg = settings.get("recording", {})
        self._save_screenshot = rec_cfg.get("save_click_screenshot", True)
        stop_key_name = rec_cfg.get("stop_key", DEFAULT_STOP_KEY)
        self._stop_key = stop_key_name.lower()

        self._event_queue: queue.Queue = queue.Queue()
        self._stop_flag = False
        self._start_time: float = 0.0
        self._events: list = []
        self._event_index = 0

    # ──────────────────────────────────────────
    # 公開API
    # ──────────────────────────────────────────

    def start(self) -> Recording:
        """記録を開始する（ブロッキング）。停止キーが押されるまで待機し、Recording を返す。"""
        rect = self._window.get_rect()
        window_title = self._window.get_title() or ""
        window_w = rect.width if rect else 0
        window_h = rect.height if rect else 0

        logger.info("=" * 50)
        logger.info("記録モード開始: '%s'", self._name)
        logger.info("  停止キー: %s", self._stop_key.upper())
        logger.info("  保存先: %s", self._output_dir)
        logger.info("=" * 50)

        self._start_time = time.time()
        self._stop_flag = False
        self._events = []
        self._event_index = 0

        mouse_listener = mouse.Listener(on_click=self._on_click)
        keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )

        mouse_listener.start()
        keyboard_listener.start()

        # pynput 起動直後に残留キーイベントを拾わないようインターバルを置く
        time.sleep(0.5)
        # sleep 中に積まれた不要イベントを破棄
        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except queue.Empty:
                break
        self._stop_flag = False  # sleep 中にセットされた可能性をリセット

        try:
            self._main_loop()
        finally:
            mouse_listener.stop()
            keyboard_listener.stop()

        total_duration = time.time() - self._start_time
        recording = Recording(
            meta=RecordingMeta(
                name=self._name,
                created_at=datetime.now(tz=timezone.utc).astimezone().isoformat(),
                window_title=window_title,
                window_width=window_w,
                window_height=window_h,
                total_duration=round(total_duration, 3),
                event_count=len(self._events),
            ),
            events=self._events,
        )

        self._save_recording(recording)
        logger.info("記録完了: %d イベント (%.1f秒)", len(self._events), total_duration)
        return recording

    # ──────────────────────────────────────────
    # メインループ（キューからイベントを取り出して処理）
    # ──────────────────────────────────────────

    def _main_loop(self) -> None:
        while not self._stop_flag:
            try:
                raw = self._event_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            try:
                if isinstance(raw, _RawClickEvent):
                    self._process_click(raw)
                elif isinstance(raw, _RawKeyEvent):
                    self._process_key(raw)
            except Exception as exc:
                logger.error("イベント処理中にエラーが発生しました（記録は継続）: %s", exc, exc_info=True)

        # フラグが立った後もキューに残ったイベントを処理する
        while not self._event_queue.empty():
            try:
                raw = self._event_queue.get_nowait()
                try:
                    if isinstance(raw, _RawClickEvent):
                        self._process_click(raw)
                    elif isinstance(raw, _RawKeyEvent):
                        self._process_key(raw)
                except Exception as exc:
                    logger.error("終了時イベント処理エラー: %s", exc)
            except queue.Empty:
                break

    # ──────────────────────────────────────────
    # イベント処理（メインスレッド）
    # ──────────────────────────────────────────

    def _process_click(self, raw: _RawClickEvent) -> None:
        self._event_index += 1
        idx = self._event_index

        screenshot = self._capture.capture()
        template_file: Optional[str] = None
        screenshot_file: Optional[str] = None

        rel_pos = self._abs_to_rel(raw.abs_x, raw.abs_y)
        if rel_pos is None:
            logger.debug("ウィンドウ外クリックをスキップ: abs=(%d,%d)", raw.abs_x, raw.abs_y)
            return

        rel_x, rel_y = rel_pos

        if screenshot is not None:
            template_file = self._extractor.extract(screenshot, rel_x, rel_y, idx)
            if self._save_screenshot:
                # スクリーンショットはテンプレートと混在しないよう記録ルートに保存する
                screenshot_file = self._extractor.save_screenshot(
                    screenshot, idx, output_dir=self._output_dir
                )

        event = ClickEvent(
            timestamp=round(raw.timestamp - self._start_time, 3),
            rel_x=rel_x,
            rel_y=rel_y,
            button=raw.button,
            template_file=template_file,
            screenshot_file=screenshot_file,
        )
        self._events.append(event)
        logger.info(
            "[記録] クリック #%d: rel=(%d,%d) template=%s",
            idx, rel_x, rel_y, template_file or "なし",
        )

    def _process_key(self, raw: _RawKeyEvent) -> None:
        if raw.action != "press":
            return  # press のみ記録
        self._event_index += 1
        event = KeyEvent(
            timestamp=round(raw.timestamp - self._start_time, 3),
            key=raw.key_str,
            action="press",
        )
        self._events.append(event)
        logger.info("[記録] キー #%d: %s", self._event_index, raw.key_str)

    # ──────────────────────────────────────────
    # pynput コールバック（別スレッド）
    # ──────────────────────────────────────────

    def _on_click(
        self,
        abs_x: int,
        abs_y: int,
        button: mouse.Button,
        pressed: bool,
    ) -> None:
        if not pressed:
            return
        btn_str = {
            mouse.Button.left: "left",
            mouse.Button.right: "right",
            mouse.Button.middle: "middle",
        }.get(button, "left")
        self._event_queue.put(_RawClickEvent(
            timestamp=time.time(),
            abs_x=abs_x,
            abs_y=abs_y,
            button=btn_str,
        ))

    def _on_key_press(self, key) -> None:
        key_str = pynput_key_to_str(key)
        if key_str is None:
            return
        # 停止キー検出
        if key_str.lower() == self._stop_key:
            logger.info("停止キー (%s) が押されました。記録を終了します...", self._stop_key.upper())
            self._stop_flag = True
            return
        self._event_queue.put(_RawKeyEvent(
            timestamp=time.time(),
            key_str=key_str,
            action="press",
        ))

    def _on_key_release(self, key) -> None:
        pass  # release は記録しない

    # ──────────────────────────────────────────
    # ユーティリティ
    # ──────────────────────────────────────────

    def _abs_to_rel(self, abs_x: int, abs_y: int) -> Optional[tuple[int, int]]:
        """スクリーン絶対座標 → ウィンドウ相対座標。ウィンドウ外なら None。"""
        rect = self._window.get_rect()
        if rect is None:
            return None
        if not (rect.left <= abs_x < rect.right and rect.top <= abs_y < rect.bottom):
            return None
        return rect.rel_point(abs_x, abs_y)

    def stop_external(self) -> None:
        """GUI ボタン等の外部スレッドから記録を停止する。

        スレッドセーフ: _stop_flag は GIL 保護下の bool 代入のため追加ロック不要。
        呼び出し後、_main_loop は次の 50ms ポーリングサイクルで終了する。
        """
        if not self._stop_flag:
            logger.info("外部から停止要求を受け付けました。記録を終了します...")
            self._stop_flag = True

    def _save_recording(self, recording: Recording) -> None:
        json_path = self._output_dir / "recording.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(recording.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info("記録を保存しました: %s", json_path)
