"""
test_recorder.py
EventRecorder の起動テスト

テスト内容:
  1. スタンドアロン（tkinter なし）
  2. tkinter メインループ稼働中
  3. customtkinter ボタンクリックで記録開始（GUI 実機相当）
  4. stop_external() の応答確認
  5. 例外が起きても記録が継続するか

使い方:
    .venv\\Scripts\\activate.bat
    python test_recorder.py
"""
from __future__ import annotations

import logging
import sys
import threading
import time
import traceback
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

# ── ログ設定（DEBUG で全出力） ──
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test")

PASS = "[PASS]"
FAIL = "[FAIL]"

results: list[tuple[str, bool]] = []


def _sep(title: str):
    print(f"\n{'='*60}\n{title}\n{'='*60}")


def make_mocks(name="test_run"):
    from core.window import GameWindow, WindowRect
    from core.capture import ScreenCapture
    from record.template_extractor import TemplateExtractor

    window_mock = MagicMock(spec=GameWindow)
    window_mock.get_rect.return_value = WindowRect(left=0, top=0, right=1920, bottom=1080)
    window_mock.get_title.return_value = "NIKKE (mock)"

    capture_mock = MagicMock(spec=ScreenCapture)
    capture_mock.capture.return_value = np.zeros((100, 100, 3), dtype=np.uint8)

    out = Path(f"test_recordings/{name}")
    (out / "templates").mkdir(parents=True, exist_ok=True)
    extractor = TemplateExtractor(output_dir=out / "templates", padding=30)

    cfg = {"recording": {"save_click_screenshot": False, "stop_key": "f9",
                          "output_dir": "test_recordings", "template_padding": 30}}
    return window_mock, capture_mock, extractor, out, cfg


def run_recorder(label: str, window, capture, extractor, output_dir, settings,
                  watch_sec=3.0) -> bool:
    from record.recorder import EventRecorder
    recorder = EventRecorder(name="test", window=window, capture=capture,
                               extractor=extractor, output_dir=output_dir, settings=settings)
    done: dict = {"at": None, "exc": None}

    def _run():
        try:
            recorder.start()
        except Exception as exc:
            done["exc"] = exc
        finally:
            done["at"] = time.time()

    t = threading.Thread(target=_run, daemon=True)
    t0 = time.time()
    t.start()
    t.join(timeout=watch_sec)
    elapsed = time.time() - t0

    if t.is_alive():
        recorder.stop_external()
        t.join(timeout=2)
        print(f"{PASS} [{label}] {watch_sec}s 後も稼働中 → 即時終了なし")
        results.append((label, True))
        return True
    else:
        print(f"{FAIL} [{label}] {elapsed:.2f}s で終了")
        if done["exc"]:
            print(f"       例外: {done['exc']}")
            traceback.print_exception(type(done["exc"]), done["exc"],
                                       done["exc"].__traceback__)
        else:
            print("       例外なし（_stop_flag=True になった = キーイベント誤検知）")
        results.append((label, False))
        return False


# ── テスト 1: スタンドアロン ──
_sep("Test 1: スタンドアロン（tkinter なし）")
run_recorder("standalone", *make_mocks("t1"))

# ── テスト 2: tkinter + customtkinter ループ稼働中 ──
_sep("Test 2: customtkinter ウィンドウ稼働中")
import customtkinter as ctk
ctk.set_appearance_mode("dark")

root = ctk.CTk()
root.geometry("200x100")
root.title("ctk test")
ctk_result: dict = {"done": False}

def _ctk_worker():
    time.sleep(0.3)
    ok = run_recorder("with-customtkinter", *make_mocks("t2"))
    ctk_result["done"] = ok
    root.after(0, root.destroy)

threading.Thread(target=_ctk_worker, daemon=True).start()
try:
    root.mainloop()
except Exception as e:
    print(f"{FAIL} customtkinter mainloop 例外: {e}")
    results.append(("with-customtkinter", False))


# ── テスト 3: ボタンクリックで記録開始（GUI 実機相当） ──
_sep("Test 3: CTkButton コマンド経由で記録開始")
root2 = ctk.CTk()
root2.geometry("300x150")
root2.title("button test")

rec_result: dict = {"ok": None}
active_recorder = None

def _on_rec_start_sim():
    """実際の GUI の _on_rec_start と同じ流れをシミュレート"""
    global active_recorder
    w, cap, ext, out, cfg = make_mocks("t3")

    def _worker():
        global active_recorder
        from record.recorder import EventRecorder
        active_recorder = EventRecorder(name="t3", window=w, capture=cap,
                                          extractor=ext, output_dir=out, settings=cfg)
        done: dict = {"at": None, "exc": None}
        def _run():
            try:
                active_recorder.start()
            except Exception as exc:
                done["exc"] = exc
            finally:
                done["at"] = time.time()
        t = threading.Thread(target=_run, daemon=True)
        t0 = time.time()
        t.start()
        t.join(timeout=3.0)
        elapsed = time.time() - t0
        if t.is_alive():
            print(f"{PASS} [button-click] 3s 後も稼働中 → 即時終了なし")
            rec_result["ok"] = True
            active_recorder.stop_external()
            t.join(timeout=2)
        else:
            print(f"{FAIL} [button-click] {elapsed:.2f}s で終了")
            if done["exc"]:
                print(f"       例外: {done['exc']}")
            else:
                print("       _stop_flag=True になった（キーイベント誤検知）")
            rec_result["ok"] = False
        results.append(("button-click", rec_result["ok"]))
        root2.after(0, root2.destroy)

    threading.Thread(target=_worker, daemon=True).start()

btn = ctk.CTkButton(root2, text="● 記録開始", command=_on_rec_start_sim)
btn.pack(pady=40)

# 0.8s 後に自動クリック
root2.after(800, btn.invoke)

try:
    root2.mainloop()
except Exception as e:
    print(f"{FAIL} mainloop 例外: {e}")
    results.append(("button-click", False))


# ── テスト 4: _process_click 例外でも継続するか ──
_sep("Test 4: _process_click 例外でも記録継続")
w4, cap4, ext4, out4, cfg4 = make_mocks("t4")
# capture が例外を投げるようにする
cap4.capture.side_effect = RuntimeError("mss mock error")

from record.recorder import EventRecorder
rec4 = EventRecorder(name="t4", window=w4, capture=cap4, extractor=ext4,
                      output_dir=out4, settings=cfg4)
done4: dict = {"at": None}

def _run4():
    rec4.start()
    done4["at"] = time.time()

t4 = threading.Thread(target=_run4, daemon=True)
t4.start()
time.sleep(0.8)

# この時点で pynput がダミークリックを出せないので、手動で _event_queue に積む
from record.recorder import _RawClickEvent
rec4._event_queue.put(_RawClickEvent(timestamp=time.time(), abs_x=100, abs_y=100, button="left"))
time.sleep(0.5)

if t4.is_alive():
    print(f"{PASS} [exception-resilience] capture 例外が出ても記録継続中")
    results.append(("exception-resilience", True))
    rec4.stop_external()
    t4.join(timeout=2)
else:
    elapsed = time.time()
    print(f"{FAIL} [exception-resilience] capture 例外で記録が終了した")
    results.append(("exception-resilience", False))


# ── 結果サマリー ──
_sep("結果サマリー")
all_pass = True
for label, ok in results:
    mark = PASS if ok else FAIL
    print(f"  {mark}  {label}")
    if not ok:
        all_pass = False

print()
if all_pass:
    print("全テスト PASS")
else:
    print("一部テスト FAIL → 上の詳細ログを確認してください")
print("=" * 60)
