"""
tasks/login_bonus.py
ログインボーナス受け取りタスク

【操作フロー】
1. ホーム画面にログインボーナスアイコンが表示されているか確認
2. アイコンをクリックしてログインボーナスダイアログを開く
3. 「まとめて受け取り」ボタンをクリック
4. 報酬アニメーション待機
5. 閉じるボタンでダイアログを閉じる

【テンプレート画像の準備】
assets/templates/login_bonus/ に以下のスクリーンショットを配置してください:
  - login_bonus_icon.png  : ホーム画面のログインボーナスアイコン
  - collect_all_button.png: 「まとめて受け取り」ボタン
  - close_button.png      : ダイアログの閉じるボタン（common/close_button.png と共有可）
"""
from __future__ import annotations

from tasks.base_task import BaseTask, TaskResult
from utils.logger import get_logger

logger = get_logger()


class LoginBonusTask(BaseTask):
    """ログインボーナスを受け取るタスク。"""

    # ─────────────────────────────────────────
    # テンプレートパスのデフォルト値
    # ─────────────────────────────────────────
    _DEFAULT_LOGIN_ICON = "assets/templates/login_bonus/login_bonus_icon.png"
    _DEFAULT_COLLECT_ALL = "assets/templates/login_bonus/collect_all_button.png"
    _DEFAULT_CLOSE = "assets/templates/common/close_button.png"
    _DEFAULT_ALREADY_RECEIVED = "assets/templates/login_bonus/already_received.png"

    def execute(self) -> TaskResult:
        """ログインボーナス受け取りフローを実行する。"""
        login_icon = self.cfg("login_icon_template", self._DEFAULT_LOGIN_ICON)
        collect_all = self.cfg("collect_all_template", self._DEFAULT_COLLECT_ALL)
        close_btn = self.cfg("close_template", self._DEFAULT_CLOSE)

        # ── Step 1: ログインボーナスアイコンが画面に存在するか確認 ──
        logger.info("[%s] ログインボーナスアイコンを探しています...", self.task_id)
        icon_match = self.wait_for(login_icon, timeout=10.0, interval=1.0)

        if icon_match is None:
            # アイコンが見当たらない = 既に受け取り済み or ホーム画面ではない
            logger.info("[%s] ログインボーナスアイコンが見つかりません（受け取り済みの可能性）", self.task_id)
            return self.skipped("ログインボーナスアイコンが見当たりません。受け取り済みか、ホーム画面ではない可能性があります。")

        # ── Step 2: アイコンをクリックしてダイアログを開く ──
        logger.info("[%s] ログインボーナスアイコンをクリック", self.task_id)
        if not self._controller.click_match(icon_match, delay=2.0):
            return self.failed("アイコンクリックに失敗しました")

        # ── Step 3: 「まとめて受け取り」ボタンを待機してクリック ──
        logger.info("[%s] 「まとめて受け取り」ボタンを待機中...", self.task_id)
        collect_match = self.wait_for(collect_all, timeout=15.0, interval=1.0)

        if collect_match is None:
            # ボタンが見つからない = 既に全部受け取り済みの場合など
            logger.info("[%s] まとめて受け取りボタンが見つかりません（全報酬受け取り済みの可能性）", self.task_id)
            # 閉じるボタンだけ押して終了
            if not self._close_dialog(close_btn):
                logger.warning("[%s] ダイアログを閉じられませんでした", self.task_id)
            return self.skipped("受け取りボタンが見つかりません。全報酬受け取り済みの可能性があります。")

        logger.info("[%s] まとめて受け取りボタンをクリック", self.task_id)
        if not self._controller.click_match(collect_match, delay=1.0):
            return self.failed("受け取りボタンのクリックに失敗しました")

        # ── Step 4: 報酬アニメーション待機 ──
        reward_wait = self._config.get("reward_animation_wait", 3.0)
        logger.info("[%s] 報酬アニメーション待機中（%.1fs）...", self.task_id, reward_wait)
        self._controller.wait(reward_wait)

        # ── Step 5: 追加の受け取りボタンがあればクリック（複数日受け取り対応）──
        logger.info("[%s] 追加の受け取り確認中...", self.task_id)
        for attempt in range(10):
            bonus_match = self.find(collect_all)
            if not bonus_match.found:
                break
            logger.info("[%s] 追加ボーナス受け取り（%d回目）", self.task_id, attempt + 1)
            self._controller.click_match(bonus_match, delay=1.5)

        # ── Step 6: ダイアログを閉じる ──
        if not self._close_dialog(close_btn):
            logger.warning("[%s] ダイアログを閉じられませんでした。次タスクに影響する可能性があります", self.task_id)

        # ── Step 7: 受け取り完了確認（アイコンが消えたか） ──
        leftover = self.find(login_icon)
        if leftover.found:
            logger.warning("[%s] アイコンがまだ表示されています。受け取りが完了していない可能性があります", self.task_id)

        return self.success("ログインボーナスの受け取りが完了しました")

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    def _close_dialog(self, close_template: str) -> bool:
        """ダイアログの閉じるボタンをクリックする。

        Returns:
            閉じるボタンを見つけてクリックした場合 True、ESCで代替した場合 False。
        """
        logger.info("[%s] ダイアログを閉じています...", self.task_id)
        close_match = self.wait_for(close_template, timeout=8.0, interval=0.8)
        if close_match:
            self._controller.click_match(close_match, delay=1.0)
            return True
        # 閉じるボタンが見つからなければESCキーで代替
        logger.warning("[%s] 閉じるボタンが見つからないため ESC を使用します", self.task_id)
        self._controller.press_escape()
        return False
