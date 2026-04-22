"""
tasks/routine_battle.py
シミュレーション室 (Simulation Room) 自動進行タスク
および前哨基地（アウトポスト）報酬回収タスク

【シミュレーション室 操作フロー】
1. ホーム画面からシミュレーション室アイコンをクリック
2. 開始ボタンを待機してクリック
3. オートバトル ON にする（既にONなら不要）
4. バトル完了（リザルト画面）を待機
5. 報酬受け取り or 次のバトルへ進む
6. 設定回数繰り返す

【テンプレート画像の準備】
assets/templates/battle/ に以下を配置:
  - start_button.png     : 開始ボタン
  - auto_button.png      : オートバトルONボタン（オフ状態のボタン画像）
  - auto_on_button.png   : オートバトルがONの状態のボタン画像（確認用）
  - battle_result.png    : バトルリザルト画面に表示される要素
  - collect_button.png   : 報酬受け取りボタン
  - next_button.png      : 次へボタン

assets/templates/navigation/ に以下を配置:
  - simulation_room_icon.png : ホームのシミュレーション室アイコン
"""
from __future__ import annotations

from tasks.base_task import BaseTask, TaskResult
from utils.logger import get_logger

logger = get_logger()


class SimulationRoomTask(BaseTask):
    """シミュレーション室の自動バトルを実行するタスク。"""

    # テンプレートのデフォルトパス
    _T_ICON = "assets/templates/navigation/simulation_room_icon.png"
    _T_START = "assets/templates/battle/start_button.png"
    _T_AUTO = "assets/templates/battle/auto_button.png"
    _T_AUTO_ON = "assets/templates/battle/auto_on_button.png"
    _T_RESULT = "assets/templates/battle/battle_result.png"
    _T_COLLECT = "assets/templates/battle/collect_button.png"
    _T_NEXT = "assets/templates/battle/next_button.png"
    _T_CLOSE = "assets/templates/common/close_button.png"

    def execute(self) -> TaskResult:
        max_battles = self.cfg("max_battles", 3)
        icon_tpl = self.cfg("simulation_icon_template", self._T_ICON)

        # ── Step 1: シミュレーション室アイコンをクリック ──
        logger.info("[%s] シミュレーション室アイコンを探しています...", self.task_id)
        icon = self.wait_for(icon_tpl, timeout=10.0, interval=1.0)
        if icon is None:
            return self.failed("シミュレーション室アイコンが見つかりません")

        self._controller.click_match(icon, delay=2.5)

        # ── Step 2〜N: バトルをmax_battles回繰り返す ──
        battles_done = 0
        for battle_num in range(1, max_battles + 1):
            logger.info("[%s] バトル %d/%d 開始", self.task_id, battle_num, max_battles)

            result = self._run_single_battle()
            if not result:
                logger.warning("[%s] バトル %d 失敗またはスキップ", self.task_id, battle_num)
                break

            battles_done += 1

            # 最後のバトルなら次へ進まない
            if battle_num < max_battles:
                # 次バトルへの遷移待機
                self._controller.wait(1.5)

        # ── シミュレーション室から戻る（ESCまたは閉じる） ──
        self._exit_to_home()

        if battles_done == 0:
            return self.failed("1回もバトルを完了できませんでした")

        return self.success(f"シミュレーション室: {battles_done}回バトル完了")

    # ──────────────────────────────────────────
    # 内部メソッド
    # ──────────────────────────────────────────

    def _run_single_battle(self) -> bool:
        """1回のバトルを実行する。成功したら True を返す。"""
        start_tpl = self.cfg("start_button_template", self._T_START)
        auto_tpl = self.cfg("auto_button_template", self._T_AUTO)
        result_tpl = self.cfg("battle_result_template", self._T_RESULT)
        collect_tpl = self.cfg("collect_template", self._T_COLLECT)
        next_tpl = self.cfg("next_button_template", self._T_NEXT)

        # 開始ボタン待機・クリック
        logger.info("[%s] 開始ボタンを待機中...", self.task_id)
        start_btn = self.wait_for(start_tpl, timeout=15.0, interval=1.0)
        if start_btn is None:
            logger.warning("[%s] 開始ボタンが見つかりません（スタミナ不足の可能性）", self.task_id)
            return False

        self._controller.click_match(start_btn, delay=2.0)

        # オートバトルが OFF なら ON にする
        auto_off = self.find(auto_tpl)
        if auto_off.found:
            logger.info("[%s] オートバトルをONにします", self.task_id)
            self._controller.click_match(auto_off, delay=0.5)

        # バトルリザルト待機（最大5分）
        battle_timeout = self.cfg("battle_timeout", 300.0)
        logger.info("[%s] バトル完了を待機中（最大%.0f秒）...", self.task_id, battle_timeout)
        result_screen = self.wait_for(result_tpl, timeout=battle_timeout, interval=3.0)

        if result_screen is None:
            logger.warning("[%s] バトルリザルト画面が表示されませんでした", self.task_id)
            return False

        logger.info("[%s] バトル完了！報酬を受け取ります", self.task_id)
        self._controller.wait(1.0)

        # 報酬受け取り or 次へ（collect は複数回ありうるが、next は1回で次画面へ移る）
        for _ in range(5):
            collect = self.find(collect_tpl)
            if collect.found:
                self._controller.click_match(collect, delay=1.5)
                continue  # 複数の報酬画面に対応
            nxt = self.find(next_tpl)
            if nxt.found:
                self._controller.click_match(nxt, delay=1.5)
                break  # next クリック後は次バトル画面へ移行するため終了
            break  # どちらも見つからなければ完了とみなす

        return True

    def _exit_to_home(self) -> None:
        """ホーム画面に戻る。"""
        close_tpl = self.cfg("close_template", self._T_CLOSE)
        logger.info("[%s] ホームに戻ります", self.task_id)
        # 閉じるボタンを試みる
        close = self.find(close_tpl)
        if close.found:
            self._controller.click_match(close, delay=1.5)
        else:
            # ESCキーで戻る
            self._controller.press_escape()
            self._controller.wait(1.0)


class OutpostTask(BaseTask):
    """前哨基地（アウトポスト）の報酬を回収するタスク。

    【操作フロー】
    1. ホームから前哨基地アイコンをクリック
    2. 報酬受け取りボタンをクリック
    3. 閉じる
    """

    _T_ICON = "assets/templates/navigation/outpost_icon.png"
    _T_COLLECT = "assets/templates/battle/collect_button.png"
    _T_CLOSE = "assets/templates/common/close_button.png"

    def execute(self) -> TaskResult:
        icon_tpl = self.cfg("outpost_icon_template", self._T_ICON)
        collect_tpl = self.cfg("collect_template", self._T_COLLECT)
        close_tpl = self.cfg("close_template", self._T_CLOSE)

        # ── Step 1: 前哨基地アイコンをクリック ──
        logger.info("[%s] 前哨基地アイコンを探しています...", self.task_id)
        icon = self.wait_for(icon_tpl, timeout=10.0, interval=1.0)
        if icon is None:
            return self.failed("前哨基地アイコンが見つかりません")

        self._controller.click_match(icon, delay=2.0)

        # ── Step 2: 報酬受け取りボタンを探してクリック ──
        logger.info("[%s] 報酬受け取りボタンを探しています...", self.task_id)
        collect = self.wait_for(collect_tpl, timeout=15.0, interval=1.0)
        if collect is None:
            logger.info("[%s] 受け取りボタンが見つかりません（報酬なし）", self.task_id)
            self._safe_close(close_tpl)
            return self.skipped("受け取れる報酬がありません")

        self._controller.click_match(collect, delay=2.0)

        # 追加の受け取り確認
        for _ in range(5):
            c = self.find(collect_tpl)
            if c.found:
                self._controller.click_match(c, delay=1.5)
            else:
                break

        # ── Step 3: 閉じる ──
        self._safe_close(close_tpl)

        return self.success("前哨基地の報酬回収が完了しました")

    def _safe_close(self, close_tpl: str) -> None:
        close = self.wait_for(close_tpl, timeout=5.0, interval=0.5)
        if close:
            self._controller.click_match(close, delay=1.0)
        else:
            self._controller.press_escape()
