"""
main.py
NIKKE 日課自動化ツール - エントリーポイント

使用例:
  # 全タスク実行
  python main.py

  # 特定タスクのみ実行
  python main.py --task login_bonus

  # テンプレートキャプチャモード（画像登録用）
  python main.py --capture

  # デバッグモード（詳細ログ）
  python main.py --debug
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml

from core.capture import ScreenCapture
from core.controller import GameController
from core.matcher import TemplateMatcher
from core.window import GameWindow
from tasks.task_runner import TaskRunner
from utils.logger import setup_logger, get_logger


# ──────────────────────────────────────────────────────────────
# 設定ロード
# ──────────────────────────────────────────────────────────────

def load_settings(path: str = "config/settings.yaml") -> dict:
    """設定ファイルを読み込む。ファイル読み込みや YAML 解析エラーを捕捉して空設定を返す。"""
    config_path = Path(path)
    logger = get_logger()

    if not config_path.exists():
        logger.warning("設定ファイルが見つかりません: %s。デフォルト設定を使用します。", path)
        return {}

    try:
        with config_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data
    except Exception as exc:  # noqa: BLE001
        logger.exception("設定ファイルの読み込みに失敗しました: %s", path)
        return {}


# ──────────────────────────────────────────────────────────────
# ゲームウィンドウ初期化
# ──────────────────────────────────────────────────────────────

def init_game(settings: dict) -> tuple[GameWindow, ScreenCapture, TemplateMatcher, GameController]:
    """ゲームウィンドウを検出し、コアオブジェクトを初期化する。"""
    logger = get_logger()

    window_cfg = settings.get("window", {})
    matching_cfg = settings.get("matching", {})
    timing_cfg = settings.get("timing", {})
    screenshot_cfg = settings.get("screenshot", {})
    log_cfg = settings.get("logging", {})

    # ウィンドウ検出（リトライあり）
    title_candidates = window_cfg.get("title_candidates", None)
    window = GameWindow(title_candidates=title_candidates)

    max_retries = window_cfg.get("find_retries", 3)
    retry_wait = window_cfg.get("find_retry_wait", 5.0)

    logger.info("NIKKEウィンドウを検出中...")
    found = False
    for attempt in range(max_retries):
        if window.find():
            found = True
            break
        if attempt < max_retries - 1:
            logger.warning(
                "ウィンドウが見つかりません。%.0f秒後に再試行します (%d/%d)...",
                retry_wait, attempt + 1, max_retries - 1,
            )
            time.sleep(retry_wait)

    if not found:
        logger.error("NIKKEが起動していないか、ウィンドウが見つかりません。")
        logger.error("NIKKEを起動してからもう一度実行してください。")
        sys.exit(1)

    if not window.focus():
        logger.warning("ウィンドウのフォーカスに失敗しました。処理を続行します。")

    # 少し待機してウィンドウが前面に来るのを待つ
    time.sleep(0.5)

    # 各モジュール初期化
    screenshot_dir = log_cfg.get("screenshot_dir", screenshot_cfg.get("save_dir", "logs/screenshots"))
    capture = ScreenCapture(window, screenshot_dir=screenshot_dir)

    default_threshold = matching_cfg.get("default_threshold", 0.80)
    matcher = TemplateMatcher(default_threshold=default_threshold)

    after_click = timing_cfg.get("after_click", 0.8)
    controller = GameController(window, after_click_delay=after_click)

    logger.info("初期化完了 - ウィンドウ: %s", window.get_rect())

    return window, capture, matcher, controller


# ──────────────────────────────────────────────────────────────
# テンプレートキャプチャモード
# ──────────────────────────────────────────────────────────────

def record_mode(
    name: str,
    window: GameWindow,
    capture: ScreenCapture,
    settings: dict,
) -> None:
    """操作記録モード。F9（デフォルト）で終了。"""
    from record.recorder import EventRecorder
    from record.template_extractor import TemplateExtractor

    logger = get_logger()
    rec_cfg = settings.get("recording", {})
    base_dir = Path(rec_cfg.get("output_dir", "recordings"))
    output_dir = base_dir / name

    if output_dir.exists():
        logger.warning("同名の記録が既に存在します: %s", output_dir)
        answer = input("上書きしますか？ [y/N]: ").strip().lower()
        if answer != "y":
            logger.info("記録をキャンセルしました")
            return

    templates_dir = output_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    padding = rec_cfg.get("template_padding", 30)
    extractor = TemplateExtractor(output_dir=templates_dir, padding=padding)
    recorder = EventRecorder(
        name=name,
        window=window,
        capture=capture,
        extractor=extractor,
        output_dir=output_dir,
        settings=settings,
    )
    recorder.start()


def play_mode(
    name: str,
    window: GameWindow,
    capture: ScreenCapture,
    matcher: TemplateMatcher,
    controller: GameController,
    speed: float,
    settings: dict,
) -> None:
    """記録再生モード。"""
    from record.player import EventPlayer

    logger = get_logger()
    rec_cfg = settings.get("recording", {})
    base_dir = Path(rec_cfg.get("output_dir", "recordings"))

    player = EventPlayer(
        name=name,
        window=window,
        capture=capture,
        matcher=matcher,
        controller=controller,
        recordings_base=base_dir,
        speed=speed,
        settings=settings,
    )
    result = player.play()
    if result.failed_count > 0:
        sys.exit(1)


def list_recordings(settings: dict) -> None:
    """保存済み記録の一覧を表示する。"""
    rec_cfg = settings.get("recording", {})
    base_dir = Path(rec_cfg.get("output_dir", "recordings"))

    if not base_dir.exists():
        print("記録がありません（recordings/ ディレクトリが存在しません）")
        return

    entries = sorted(base_dir.iterdir())
    recordings = [d for d in entries if d.is_dir() and (d / "recording.json").exists()]

    if not recordings:
        print("記録がありません")
        return

    print(f"{'名前':<20} {'作成日時':<26} {'イベント数':>10} {'秒数':>8}")
    print("─" * 68)
    for rec_dir in recordings:
        try:
            with (rec_dir / "recording.json").open(encoding="utf-8") as f:
                meta = json.load(f).get("meta", {})
            print(
                f"{meta.get('name', rec_dir.name):<20} "
                f"{meta.get('created_at', '-'):<26} "
                f"{meta.get('event_count', 0):>10} "
                f"{meta.get('total_duration', 0.0):>8.1f}s"
            )
        except Exception:  # noqa: BLE001
            print(f"{rec_dir.name:<20} (読み込み失敗)")


def capture_mode(capture: ScreenCapture) -> None:
    """テンプレート画像の登録用キャプチャモード。

    画面全体のスクリーンショットを撮影し、
    assets/templates/captures/ に保存する。
    """
    logger = get_logger()
    logger.info("=" * 50)
    logger.info("テンプレートキャプチャモード")
    logger.info("  - スクリーンショットを撮影して保存します")
    logger.info("  - 保存先: assets/templates/captures/")
    logger.info("  - 終了: Ctrl+C")
    logger.info("=" * 50)

    capture_dir = Path("assets/templates/captures")
    capture_dir.mkdir(parents=True, exist_ok=True)

    # キャプチャ専用のScreenCaptureインスタンスを作成
    from datetime import datetime
    import cv2

    count = 0
    while True:
        try:
            input(f"\n[{count + 1}] Enterキーでスクリーンショット撮影（Ctrl+C で終了）")
            img = capture.capture()
            if img is None:
                logger.error("キャプチャ失敗")
                continue

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = capture_dir / f"capture_{ts}.png"
            cv2.imwrite(str(path), img)
            logger.info("保存しました: %s", path)
            count += 1

        except KeyboardInterrupt:
            logger.info("\nキャプチャモードを終了します（%d枚保存）", count)
            break


# ──────────────────────────────────────────────────────────────
# メインエントリーポイント
# ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="NIKKE 日課自動化ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python main.py                      # 全タスク実行
  python main.py --task login_bonus   # ログインボーナスのみ
  python main.py --capture            # テンプレートキャプチャモード
  python main.py --debug              # デバッグログ有効
        """,
    )
    parser.add_argument(
        "--task",
        metavar="TASK_ID",
        help="実行するタスクIDを指定（省略時は全タスク実行）",
    )
    parser.add_argument(
        "--capture",
        action="store_true",
        help="テンプレート画像登録用のキャプチャモードで起動",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグレベルのログを出力する",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="タスク失敗時に後続タスクを中断する",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="設定ファイルのパス（デフォルト: config/settings.yaml）",
    )
    parser.add_argument(
        "--tasks-config",
        default="config/tasks.yaml",
        help="タスク設定ファイルのパス（デフォルト: config/tasks.yaml）",
    )

    # 記録・再生モード
    rec_group = parser.add_argument_group("記録・再生モード")
    rec_group.add_argument(
        "--record",
        metavar="NAME",
        help="操作を記録する。recordings/<NAME>/ に保存。停止: F9キー",
    )
    rec_group.add_argument(
        "--play",
        metavar="NAME",
        help="recordings/<NAME>/recording.json を再生する",
    )
    rec_group.add_argument(
        "--speed",
        type=float,
        default=1.0,
        metavar="FACTOR",
        help="再生速度倍率（--play と併用。デフォルト: 1.0）",
    )
    rec_group.add_argument(
        "--list-recordings",
        action="store_true",
        help="保存済みの記録一覧を表示する",
    )

    args = parser.parse_args()

    # 設定読み込み
    settings = load_settings(args.config)
    log_cfg = settings.get("logging", {})
    log_level = "DEBUG" if args.debug else log_cfg.get("level", "INFO")

    # ロガー初期化
    setup_logger(
        level=log_level,
        log_dir=log_cfg.get("log_dir", "logs"),
        screenshot_on_error=log_cfg.get("screenshot_on_error", True),
    )
    logger = get_logger()

    logger.info("━" * 50)
    logger.info("  NIKKE 日課自動化ツール v1.0")
    logger.info("━" * 50)

    # 記録一覧はウィンドウ不要
    if args.list_recordings:
        list_recordings(settings)
        return

    # ゲーム初期化
    window, capture, matcher, controller = init_game(settings)

    # キャプチャモード
    if args.capture:
        capture_mode(capture)
        return

    # 記録モード
    if args.record:
        logger.info("記録モード: '%s'", args.record)
        record_mode(args.record, window, capture, settings)
        return

    # 再生モード
    if args.play:
        logger.info("再生モード: '%s' (speed=%.1fx)", args.play, args.speed)
        play_mode(args.play, window, capture, matcher, controller, args.speed, settings)
        return

    # タスクランナー起動
    runner = TaskRunner(
        window=window,
        capture=capture,
        matcher=matcher,
        controller=controller,
        tasks_config_path=args.tasks_config,
        stop_on_failure=args.stop_on_failure,
    )

    if args.task:
        # 特定タスクのみ実行
        logger.info("指定タスクを実行: %s", args.task)
        result = runner.run_task(args.task)
        if result is None:
            sys.exit(1)
        sys.exit(0 if result.succeeded else 1)
    else:
        # 全タスク実行
        results = runner.run_all()
        failed = sum(1 for r in results if r.status.value == "failed")
        sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
