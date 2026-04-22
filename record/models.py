"""
record/models.py
記録・再生データモデル
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal, Union

# pynput → pyautogui キー名変換テーブル
PYNPUT_TO_PYAUTOGUI: dict[str, str] = {
    "Key.alt": "alt",
    "Key.alt_l": "altleft",
    "Key.alt_r": "altright",
    "Key.backspace": "backspace",
    "Key.caps_lock": "capslock",
    "Key.ctrl": "ctrl",
    "Key.ctrl_l": "ctrlleft",
    "Key.ctrl_r": "ctrlright",
    "Key.delete": "delete",
    "Key.down": "down",
    "Key.end": "end",
    "Key.enter": "enter",
    "Key.esc": "escape",
    "Key.escape": "escape",
    "Key.f1": "f1",
    "Key.f2": "f2",
    "Key.f3": "f3",
    "Key.f4": "f4",
    "Key.f5": "f5",
    "Key.f6": "f6",
    "Key.f7": "f7",
    "Key.f8": "f8",
    "Key.f9": "f9",
    "Key.f10": "f10",
    "Key.f11": "f11",
    "Key.f12": "f12",
    "Key.home": "home",
    "Key.insert": "insert",
    "Key.left": "left",
    "Key.media_next": "nexttrack",
    "Key.media_play_pause": "playpause",
    "Key.media_previous": "prevtrack",
    "Key.menu": "apps",
    "Key.num_lock": "numlock",
    "Key.page_down": "pagedown",
    "Key.page_up": "pageup",
    "Key.pause": "pause",
    "Key.print_screen": "printscreen",
    "Key.right": "right",
    "Key.scroll_lock": "scrolllock",
    "Key.shift": "shift",
    "Key.shift_l": "shiftleft",
    "Key.shift_r": "shiftright",
    "Key.space": "space",
    "Key.tab": "tab",
    "Key.up": "up",
    "Key.win": "win",
    "Key.win_l": "winleft",
    "Key.win_r": "winright",
}


def pynput_key_to_str(key) -> str | None:
    """pynput のキーオブジェクトを pyautogui キー名文字列に変換する。

    変換できない場合は None を返す。
    """
    raw = str(key)
    if raw in PYNPUT_TO_PYAUTOGUI:
        return PYNPUT_TO_PYAUTOGUI[raw]
    # 文字キー: "'a'" → "a"
    stripped = raw.strip("'")
    if len(stripped) == 1 and stripped.isprintable():
        return stripped
    return None


# ──────────────────────────────────────────
# イベントデータクラス
# ──────────────────────────────────────────

@dataclass
class ClickEvent:
    type: Literal["click"] = field(default="click", init=False)
    timestamp: float = 0.0
    rel_x: int = 0
    rel_y: int = 0
    button: str = "left"
    template_file: str | None = None
    screenshot_file: str | None = None


@dataclass
class KeyEvent:
    type: Literal["key"] = field(default="key", init=False)
    timestamp: float = 0.0
    key: str = ""
    action: Literal["press", "release"] = "press"


RecordingEvent = Union[ClickEvent, KeyEvent]


# ──────────────────────────────────────────
# メタデータ・記録全体
# ──────────────────────────────────────────

@dataclass
class RecordingMeta:
    name: str = ""
    created_at: str = ""
    window_title: str = ""
    window_width: int = 0
    window_height: int = 0
    total_duration: float = 0.0
    event_count: int = 0
    tool_version: str = "1.0"


@dataclass
class Recording:
    meta: RecordingMeta = field(default_factory=RecordingMeta)
    events: list[RecordingEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        # dataclass の type フィールドは init=False なので asdict で含まれる
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Recording":
        meta = RecordingMeta(**d["meta"])
        events: list[RecordingEvent] = []
        for e in d.get("events", []):
            t = e.get("type")
            e_copy = {k: v for k, v in e.items() if k != "type"}
            if t == "click":
                events.append(ClickEvent(**e_copy))
            elif t == "key":
                events.append(KeyEvent(**e_copy))
        return cls(meta=meta, events=events)
