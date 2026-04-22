"""
tasks/tribe_tower.py
部族タワー デイリー挑戦タスク（未実装）

【テンプレート画像の準備】
assets/templates/navigation/ に以下を配置:
  - tribe_tower_icon.png     : ホームの部族タワーアイコン

assets/templates/battle/ に以下を配置:
  - challenge_button.png     : 挑戦ボタン
  - auto_clear_button.png    : オートクリアボタン
  - battle_result.png        : バトルリザルト画面要素
"""
from __future__ import annotations

from tasks.base_task import BaseTask, TaskResult
from utils.logger import get_logger

logger = get_logger()


class TribeTowerTask(BaseTask):
    """部族タワーのデイリー挑戦タスク。

    現在未実装。tasks.yaml で enabled: false に設定されている間は実行されない。
    実装完了後に enabled: true に変更して使用すること。
    """

    _T_ICON = "assets/templates/navigation/tribe_tower_icon.png"
    _T_CHALLENGE = "assets/templates/battle/challenge_button.png"
    _T_AUTO_CLEAR = "assets/templates/battle/auto_clear_button.png"
    _T_RESULT = "assets/templates/battle/battle_result.png"

    def execute(self) -> TaskResult:
        logger.warning("[%s] 部族タワータスクは未実装です", self.task_id)
        return self.skipped("部族タワータスクは未実装です。tasks.yaml の enabled を false のままにしてください。")
