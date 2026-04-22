# NIKKE 日課自動化ツール

NIKKEのPC版クライアントで日課作業（ログインボーナス受け取り・ルーティンバトル進行等）を自動化するツールです。  
**ゲーム内ロジックへのアクセスは一切行わず、画面認識（テンプレートマッチング）と外部入力（マウス・キーボード操作）のみで動作します。**

---

## 仕組み

```
[スクリーンショット撮影] → [OpenCVでUI要素を検出] → [PyAutoGUIでクリック操作]
```

ゲームのメモリやファイルには一切触れません。「人間が目で見てクリックする操作」をPythonで再現します。

---

## 対応タスク

| タスクID | 内容 | デフォルト |
|---|---|---|
| `login_bonus` | ログインボーナスの受け取り | 有効 |
| `simulation_room` | シミュレーション室の自動バトル | 有効 |
| `outpost_reward` | 前哨基地の報酬回収 | 有効 |
| `tribe_tower` | 部族タワーのデイリー挑戦 | 無効（設定後に有効化） |

---

## セットアップ手順

### 1. 初回セットアップ

```bat
setup.bat
```

Python仮想環境の作成・ライブラリのインストール・ディレクトリ作成を自動で行います。

### 2. テンプレート画像の登録（重要）

ツールはUI要素を「画像認識」で探します。そのための **テンプレート画像** を事前に登録する必要があります。

**手順:**

1. NIKKEを起動し、**登録したい画面**（ホーム画面など）を表示する
2. `run_capture.bat` を実行する
3. `Enter` を押してスクリーンショットを撮影する（`assets/templates/captures/` に保存される）
4. 撮影した画像から必要なUI要素部分を切り取り、対応するフォルダに保存する

**必要なテンプレート画像一覧:**

```
assets/templates/
├── login_bonus/
│   ├── login_bonus_icon.png       ← ホーム画面のログインボーナスアイコン
│   └── collect_all_button.png     ← 「まとめて受け取り」ボタン
├── battle/
│   ├── start_button.png           ← 開始ボタン
│   ├── auto_button.png            ← オートバトルOFF状態のボタン
│   ├── battle_result.png          ← リザルト画面の特徴的な部分
│   └── collect_button.png         ← 報酬受け取りボタン
├── navigation/
│   ├── simulation_room_icon.png   ← シミュレーション室アイコン
│   └── outpost_icon.png           ← 前哨基地アイコン
└── common/
    └── close_button.png           ← 閉じる（×）ボタン
```

> **ヒント**: 画像はできるだけ小さく切り取ってください（ボタン部分だけでOK）。周囲の余白が多いと誤認識の原因になります。

### 3. 動作確認

画像を登録したら、まず1つのタスクだけ試してみましょう：

```bat
.venv\Scripts\activate.bat
python main.py --task login_bonus --debug
```

---

## 使い方

### 全タスク実行

```bat
run.bat
```

または:
```bat
.venv\Scripts\activate.bat
python main.py
```

### 特定タスクのみ実行

```bat
python main.py --task login_bonus
python main.py --task simulation_room
python main.py --task outpost_reward
```

### デバッグモード（詳細ログ）

```bat
python main.py --debug
```

### オプション一覧

```
--task TASK_ID      特定タスクのみ実行
--capture           テンプレートキャプチャモード
--debug             デバッグログを有効化
--stop-on-failure   タスク失敗時に後続を中断
--config PATH       設定ファイルのパス指定
--tasks-config PATH タスク設定ファイルのパス指定
```

---

## 設定のカスタマイズ

### config/settings.yaml

| 設定 | 説明 | デフォルト |
|---|---|---|
| `matching.default_threshold` | 画像認識の一致度閾値（高いほど厳格） | 0.80 |
| `matching.wait_timeout` | UI要素の待機タイムアウト（秒） | 30 |
| `timing.after_click` | クリック後の待機時間（秒） | 0.8 |
| `timing.screen_transition` | 画面遷移待機時間（秒） | 2.0 |

### config/tasks.yaml

各タスクの `enabled: true/false` で実行のON/OFFを切り替えられます。

---

## 緊急停止

**マウスを画面の左上隅（座標 0,0）に素早く移動させる**と、PyAutoGUIのフェールセーフ機能が働いて即座に停止します。

---

## ディレクトリ構成

```
nikke-automation/
├── main.py                    # エントリーポイント
├── requirements.txt
├── setup.bat                  # 初回セットアップ
├── run.bat                    # 実行ショートカット
├── run_capture.bat            # テンプレートキャプチャ
├── config/
│   ├── settings.yaml          # 動作設定
│   └── tasks.yaml             # タスク定義
├── core/
│   ├── window.py              # ウィンドウ検出
│   ├── capture.py             # スクリーンキャプチャ
│   ├── matcher.py             # テンプレートマッチング
│   └── controller.py          # マウス・キーボード操作
├── tasks/
│   ├── base_task.py           # タスク基底クラス
│   ├── login_bonus.py         # ログインボーナスタスク
│   ├── routine_battle.py      # シミュレーション室・前哨基地タスク
│   └── task_runner.py         # タスクランナー
├── utils/
│   └── logger.py              # ロギング
├── assets/
│   └── templates/             # テンプレート画像（要登録）
└── logs/                      # 実行ログ・スクリーンショット
```

---

## トラブルシューティング

**「NIKKEウィンドウが見つかりません」**  
→ NIKKEを起動してからツールを実行してください。ウィンドウタイトルが変わっている場合は `config/settings.yaml` の `window.title_candidates` を更新してください。

**「テンプレートが見つかりません」と表示され動かない**  
→ `assets/templates/` に対応する画像が保存されているか確認してください。`run_capture.bat` で画面を撮影し、切り取って登録してください。

**クリックが意図しない場所に当たる**  
→ ゲームのウィンドウサイズ・解像度を変えないようにしてください。`config/settings.yaml` の `matching.default_threshold` を少し下げる（例: 0.75）と認識しやすくなります。

**実行中に止まってしまう**  
→ `--debug` オプションで詳細ログを確認してください。`logs/screenshots/` にエラー時の画面が保存されます。

---

## 新しいタスクの追加方法

1. `tasks/` に新しいPythonファイルを作成（`BaseTask` を継承）
2. `execute()` メソッドを実装
3. `config/tasks.yaml` にタスク定義を追加

```python
# tasks/my_task.py
from tasks.base_task import BaseTask, TaskResult

class MyTask(BaseTask):
    def execute(self) -> TaskResult:
        # テンプレートを探してクリック
        if not self.find_and_click("assets/templates/my_button.png"):
            return self.failed("ボタンが見つかりません")
        return self.success("完了しました")
```

---

*本ツールは個人利用を目的としています。ゲームの利用規約を確認の上ご使用ください。*
