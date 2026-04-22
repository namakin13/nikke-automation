"""
gui/app.py
NIKKE Automation - メインウィンドウ (customtkinter)

スレッド設計:
  メインスレッド (Tk イベントループ) のみ UI を操作する。
  接続・記録・再生はそれぞれ daemon スレッドで実行し、
  完了 / エラー時は self.after(0, callback) でメインスレッドに委譲する。
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from gui.log_handler import QueueLogHandler

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── UI 定数 ──
WIN_W, WIN_H = 760, 620
LEFT_W = 280
COLOR_OK = "#2ecc71"
COLOR_ERR = "#e74c3c"
COLOR_WARN = "#f39c12"
COLOR_GRAY = "#7f8c8d"


class NikkeAutomationApp(ctk.CTk):

    # ── 状態定数 ──
    IDLE = "idle"
    CONNECTING = "connecting"
    RECORDING = "recording"
    PLAYING = "playing"

    def __init__(self) -> None:
        super().__init__()

        self._settings = self._load_settings()
        self._state = self.IDLE
        self._recorder = None
        self._record_thread: Optional[threading.Thread] = None
        self._play_thread: Optional[threading.Thread] = None

        # コアコンポーネント（接続後に設定）
        self._window = None
        self._capture = None
        self._matcher = None
        self._controller = None

        # ログ
        self._log_handler = QueueLogHandler()
        self._log_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
        ))
        self._setup_log_handler()

        self._build_ui()
        self._after_poll_log()
        self._after_poll_status()
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ──────────────────────────────────────────
    # 初期化
    # ──────────────────────────────────────────

    def _load_settings(self) -> dict:
        try:
            import yaml
            with open("config/settings.yaml", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _setup_log_handler(self) -> None:
        logger = logging.getLogger("nikke_auto")
        if self._log_handler not in logger.handlers:
            logger.addHandler(self._log_handler)

    # ──────────────────────────────────────────
    # UI 構築
    # ──────────────────────────────────────────

    def _build_ui(self) -> None:
        self.title("NIKKE Automation")
        self.geometry(f"{WIN_W}x{WIN_H}")
        self.resizable(True, True)
        self.minsize(WIN_W, WIN_H)

        icon_path = Path("assets/icon.ico")
        if icon_path.exists():
            self.iconbitmap(str(icon_path))

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_pane()
        self._build_right_pane()

    def _build_left_pane(self) -> None:
        left = ctk.CTkFrame(self, width=LEFT_W, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)  # spacer

        self._build_status_card(left, row=0)
        self._build_record_card(left, row=1)
        self._build_play_card(left, row=2)

    def _build_status_card(self, parent: ctk.CTkFrame, row: int) -> None:
        card = self._card(parent, row)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="NIKKE Automation",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(14, 4), sticky="w")

        self._status_dot = ctk.CTkLabel(
            card, text="● 未接続", text_color=COLOR_ERR,
            font=ctk.CTkFont(size=12),
        )
        self._status_dot.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="w")

        self._btn_connect = ctk.CTkButton(
            card, text="接続", width=80, height=30,
            command=self._on_connect,
        )
        self._btn_connect.grid(row=1, column=1, padx=14, pady=(0, 10))

    def _build_record_card(self, parent: ctk.CTkFrame, row: int) -> None:
        card = self._card(parent, row)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="操作記録",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(12, 6), sticky="w")

        ctk.CTkLabel(card, text="記録名").grid(row=1, column=0, padx=14, sticky="w")
        self._entry_rec_name = ctk.CTkEntry(
            card, placeholder_text="例: daily_routine",
        )
        self._entry_rec_name.insert(0, "my_routine")
        self._entry_rec_name.grid(row=2, column=0, columnspan=2, padx=14, pady=(4, 8), sticky="ew")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 4), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self._btn_rec_start = ctk.CTkButton(
            btn_row, text="● 記録開始",
            fg_color=COLOR_ERR, hover_color="#c0392b",
            command=self._on_rec_start, state="disabled",
        )
        self._btn_rec_start.grid(row=0, column=0, padx=(0, 3), sticky="ew")

        self._btn_rec_stop = ctk.CTkButton(
            btn_row, text="■ 停止",
            command=self._on_rec_stop, state="disabled",
        )
        self._btn_rec_stop.grid(row=0, column=1, padx=(3, 0), sticky="ew")

        ctk.CTkLabel(
            card, text="停止: F9 または「■ 停止」ボタン",
            text_color=COLOR_GRAY, font=ctk.CTkFont(size=11),
        ).grid(row=4, column=0, columnspan=2, padx=14, pady=(2, 12))

    def _build_play_card(self, parent: ctk.CTkFrame, row: int) -> None:
        card = self._card(parent, row)
        card.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.grid(row=0, column=0, columnspan=2, padx=14, pady=(12, 6), sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="記録再生",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        self._btn_refresh = ctk.CTkButton(
            hdr, text="↺", width=32, height=26,
            command=self._refresh_recordings,
        )
        self._btn_refresh.grid(row=0, column=1)

        self._combo_recordings = ctk.CTkComboBox(
            card, values=[], state="readonly",
            command=self._on_recording_selected,
        )
        self._combo_recordings.grid(row=1, column=0, columnspan=2, padx=14, pady=(0, 8), sticky="ew")

        spd_row = ctk.CTkFrame(card, fg_color="transparent")
        spd_row.grid(row=2, column=0, columnspan=2, padx=14, pady=(0, 8), sticky="ew")
        spd_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(spd_row, text="速度").grid(row=0, column=0, padx=(0, 8))
        self._slider_speed = ctk.CTkSlider(
            spd_row, from_=0.25, to=3.0, number_of_steps=11,
            command=self._on_speed_change,
        )
        self._slider_speed.set(1.0)
        self._slider_speed.grid(row=0, column=1, sticky="ew")
        self._lbl_speed = ctk.CTkLabel(spd_row, text="1.0x", width=38)
        self._lbl_speed.grid(row=0, column=2, padx=(6, 0))

        self._btn_play = ctk.CTkButton(
            card, text="▶  実行",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40, command=self._on_play, state="disabled",
        )
        self._btn_play.grid(row=3, column=0, columnspan=2, padx=14, pady=(4, 14), sticky="ew")

        self._refresh_recordings()

    def _build_right_pane(self) -> None:
        right = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="ログ出力",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr, text="クリア", width=56, height=26,
            command=self._clear_log,
        ).grid(row=0, column=1)

        self._textbox_log = ctk.CTkTextbox(
            right, state="disabled",
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self._textbox_log.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")

    # ──────────────────────────────────────────
    # ヘルパー
    # ──────────────────────────────────────────

    def _card(self, parent: ctk.CTkFrame, row: int) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        frame.grid(row=row, column=0, padx=10, pady=6, sticky="ew")
        return frame

    # ──────────────────────────────────────────
    # 接続
    # ──────────────────────────────────────────

    def _on_connect(self) -> None:
        self._set_state(self.CONNECTING)

        def _worker() -> None:
            try:
                from core.window import GameWindow
                from core.capture import ScreenCapture
                from core.matcher import TemplateMatcher
                from core.controller import GameController
                from utils.logger import setup_logger
                import time

                log_cfg = self._settings.get("logging", {})
                setup_logger(
                    level=log_cfg.get("level", "INFO"),
                    log_dir=log_cfg.get("log_dir", "logs"),
                )

                window_cfg = self._settings.get("window", {})
                window = GameWindow(title_candidates=window_cfg.get("title_candidates"))

                max_retries = window_cfg.get("find_retries", 3)
                retry_wait = window_cfg.get("find_retry_wait", 5.0)
                found = False
                for attempt in range(max_retries):
                    if window.find():
                        found = True
                        break
                    if attempt < max_retries - 1:
                        self.after(0, lambda a=attempt, t=max_retries - 1: self._append_log(
                            f"ウィンドウ未検出。再試行 {a+1}/{t}..."
                        ))
                        time.sleep(retry_wait)

                if not found:
                    self.after(0, self._on_connect_fail)
                    return

                window.focus()
                time.sleep(0.3)

                m_cfg = self._settings.get("matching", {})
                t_cfg = self._settings.get("timing", {})
                l_cfg = self._settings.get("logging", {})

                capture = ScreenCapture(
                    window,
                    screenshot_dir=l_cfg.get("screenshot_dir", "logs/screenshots"),
                )
                matcher = TemplateMatcher(default_threshold=m_cfg.get("default_threshold", 0.80))
                controller = GameController(window, after_click_delay=t_cfg.get("after_click", 0.8))

                self._window = window
                self._capture = capture
                self._matcher = matcher
                self._controller = controller
                self.after(0, self._on_connect_ok)

            except Exception as exc:
                self.after(0, lambda: self._on_connect_error(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_connect_ok(self) -> None:
        self._status_dot.configure(text="● 接続済み", text_color=COLOR_OK)
        self._btn_connect.configure(text="再接続")
        self._set_state(self.IDLE)
        self._append_log("NIKKEウィンドウに接続しました")

    def _on_connect_fail(self) -> None:
        self._status_dot.configure(text="● 未接続", text_color=COLOR_ERR)
        self._set_state(self.IDLE)
        self._append_log("[エラー] NIKKEウィンドウが見つかりません。ゲームを起動してください。")

    def _on_connect_error(self, exc: Exception) -> None:
        self._status_dot.configure(text="● エラー", text_color=COLOR_WARN)
        self._set_state(self.IDLE)
        self._append_log(f"[エラー] 接続失敗: {exc}")

    # ──────────────────────────────────────────
    # 記録
    # ──────────────────────────────────────────

    def _on_rec_start(self) -> None:
        name = self._entry_rec_name.get().strip()
        if not name:
            messagebox.showwarning("入力エラー", "記録名を入力してください")
            return

        rec_cfg = self._settings.get("recording", {})
        base_dir = Path(rec_cfg.get("output_dir", "recordings"))
        if (base_dir / name).exists():
            if not messagebox.askyesno("確認", f"「{name}」は既に存在します。\n上書きしますか？"):
                return

        self._set_state(self.RECORDING)
        self._append_log(f"記録開始: {name}  （停止: F9 または「■ 停止」ボタン）")

        def _worker() -> None:
            try:
                from record.recorder import EventRecorder
                from record.template_extractor import TemplateExtractor

                rec_cfg = self._settings.get("recording", {})
                base_dir = Path(rec_cfg.get("output_dir", "recordings"))
                output_dir = base_dir / name
                templates_dir = output_dir / "templates"
                templates_dir.mkdir(parents=True, exist_ok=True)

                extractor = TemplateExtractor(
                    output_dir=templates_dir,
                    padding=rec_cfg.get("template_padding", 30),
                )
                recorder = EventRecorder(
                    name=name,
                    window=self._window,
                    capture=self._capture,
                    extractor=extractor,
                    output_dir=output_dir,
                    settings=self._settings,
                )
                self._recorder = recorder
                recorder.start()  # ブロッキング

            except Exception as exc:
                self.after(0, lambda: self._append_log(f"[エラー] 記録失敗: {exc}"))
            finally:
                self.after(0, self._on_rec_done)

        self._record_thread = threading.Thread(target=_worker, daemon=True)
        self._record_thread.start()

    def _on_rec_stop(self) -> None:
        if self._recorder is not None:
            self._recorder.stop_external()

    def _on_rec_done(self) -> None:
        self._recorder = None
        self._set_state(self.IDLE)
        self._refresh_recordings()
        self._append_log("記録が完了しました")

    # ──────────────────────────────────────────
    # 再生
    # ──────────────────────────────────────────

    def _on_play(self) -> None:
        name = self._combo_recordings.get().strip()
        if not name:
            messagebox.showwarning("選択エラー", "再生する記録を選択してください")
            return

        speed = round(self._slider_speed.get(), 2)
        self._set_state(self.PLAYING)
        self._append_log(f"再生開始: {name}  (速度: {speed}x)")

        def _worker() -> None:
            result = None
            try:
                from record.player import EventPlayer

                rec_cfg = self._settings.get("recording", {})
                base_dir = Path(rec_cfg.get("output_dir", "recordings"))

                player = EventPlayer(
                    name=name,
                    window=self._window,
                    capture=self._capture,
                    matcher=self._matcher,
                    controller=self._controller,
                    recordings_base=base_dir,
                    speed=speed,
                    settings=self._settings,
                )
                result = player.play()

            except Exception as exc:
                self.after(0, lambda: self._append_log(f"[エラー] 再生失敗: {exc}"))
            finally:
                self.after(0, lambda: self._on_play_done(result))

        self._play_thread = threading.Thread(target=_worker, daemon=True)
        self._play_thread.start()

    def _on_play_done(self, result) -> None:
        self._set_state(self.IDLE)
        if result:
            self._append_log(
                f"再生完了: {result.played}/{result.total_events} イベント "
                f"| フォールバック: {result.fallback_count} "
                f"| 失敗: {result.failed_count}"
            )
        else:
            self._append_log("再生が終了しました")

    # ──────────────────────────────────────────
    # 記録一覧
    # ──────────────────────────────────────────

    def _refresh_recordings(self) -> None:
        rec_cfg = self._settings.get("recording", {})
        base_dir = Path(rec_cfg.get("output_dir", "recordings"))

        names: list[str] = []
        if base_dir.exists():
            names = sorted(
                d.name for d in base_dir.iterdir()
                if d.is_dir() and (d / "recording.json").exists()
            )

        self._combo_recordings.configure(values=names)
        if names:
            current = self._combo_recordings.get()
            if current not in names:
                self._combo_recordings.set(names[-1])
        else:
            self._combo_recordings.set("")

        self._update_play_btn()

    def _on_recording_selected(self, _value: str) -> None:
        self._update_play_btn()

    # ──────────────────────────────────────────
    # 状態管理
    # ──────────────────────────────────────────

    def _set_state(self, state: str) -> None:
        self._state = state
        connected = self._window is not None

        if state == self.IDLE:
            self._btn_connect.configure(state="normal")
            self._entry_rec_name.configure(state="normal")
            self._btn_rec_start.configure(state="normal" if connected else "disabled")
            self._btn_rec_stop.configure(state="disabled")
            self._combo_recordings.configure(state="readonly")
            self._slider_speed.configure(state="normal")
            self._btn_refresh.configure(state="normal")
            self._update_play_btn()

        elif state == self.CONNECTING:
            self._btn_connect.configure(state="disabled", text="接続中...")
            self._btn_rec_start.configure(state="disabled")
            self._btn_play.configure(state="disabled")

        elif state == self.RECORDING:
            self._btn_connect.configure(state="disabled")
            self._entry_rec_name.configure(state="disabled")
            self._btn_rec_start.configure(state="disabled")
            self._btn_rec_stop.configure(state="normal")
            self._combo_recordings.configure(state="disabled")
            self._btn_refresh.configure(state="disabled")
            self._btn_play.configure(state="disabled")

        elif state == self.PLAYING:
            self._btn_connect.configure(state="disabled")
            self._btn_rec_start.configure(state="disabled")
            self._combo_recordings.configure(state="disabled")
            self._slider_speed.configure(state="disabled")
            self._btn_refresh.configure(state="disabled")
            self._btn_play.configure(state="disabled", text="再生中...")

    def _update_play_btn(self) -> None:
        has_rec = bool(self._combo_recordings.get().strip())
        connected = self._window is not None
        ok = has_rec and connected and self._state == self.IDLE
        self._btn_play.configure(
            state="normal" if ok else "disabled",
            text="▶  実行",
        )

    def _on_speed_change(self, value: float) -> None:
        self._lbl_speed.configure(text=f"{value:.2f}x")

    # ──────────────────────────────────────────
    # ログ
    # ──────────────────────────────────────────

    def _append_log(self, message: str) -> None:
        self._textbox_log.configure(state="normal")
        self._textbox_log.insert("end", message + "\n")
        self._textbox_log.see("end")
        self._textbox_log.configure(state="disabled")

    def _clear_log(self) -> None:
        self._textbox_log.configure(state="normal")
        self._textbox_log.delete("1.0", "end")
        self._textbox_log.configure(state="disabled")

    def _after_poll_log(self) -> None:
        """100ms ごとにログキューを drain して TextBox に追記する。"""
        try:
            while True:
                msg = self._log_handler.queue.get_nowait()
                self._append_log(msg)
        except Exception:
            pass
        self.after(100, self._after_poll_log)

    # ──────────────────────────────────────────
    # NIKKE 生存監視
    # ──────────────────────────────────────────

    def _after_poll_status(self) -> None:
        """2 秒ごとに NIKKE ウィンドウの生存を確認する。"""
        if self._window is not None and not self._window.is_alive():
            self._window = None
            self._capture = None
            self._matcher = None
            self._controller = None
            self._status_dot.configure(text="● 未接続", text_color=COLOR_ERR)
            self._btn_connect.configure(text="接続")
            if self._state == self.IDLE:
                self._btn_rec_start.configure(state="disabled")
                self._update_play_btn()
            self._append_log("[警告] NIKKEウィンドウが閉じられました")
        self.after(2000, self._after_poll_status)

    # ──────────────────────────────────────────
    # ウィンドウ終了
    # ──────────────────────────────────────────

    def _on_closing(self) -> None:
        if self._state in (self.RECORDING, self.PLAYING):
            if not messagebox.askyesno(
                "終了確認",
                "現在操作が実行中です。\n終了してもよいですか？",
            ):
                return
            if self._recorder:
                self._recorder.stop_external()

        logging.getLogger("nikke_auto").removeHandler(self._log_handler)
        self.destroy()
