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
| `tribe_tower` | 部族タワーのデイリー挑戦 | 無効（未実装） |

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
2. `run_capture.bat` を実行してスクリーンショットを撮影する（`assets/templates/captures/` に保存される）
3. 撮影した画像から必要なUI要素部分を切り取り、対応するフォルダに保存する

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

```bat
.venv\Scripts\activate.bat
python main.py --task login_bonus --debug
```

---

## 使い方

### GUI（推奨）

```bat
python gui_main.py
```

または配布用の実行ファイル：

```
dist\NikkeAutomation\NikkeAutomation.exe
```

GUIでは以下の操作ができます：

- **タスク実行** — 有効なタスクをすべて順番に実行
- **操作記録の開始・停止** — マウス操作とキー入力を記録（F9で停止）
- **記録の再生** — 保存した操作記録をテンプレートマッチングで再生
- **ログ表示** — リアルタイムでログを確認

### コマンドライン

#### 全タスク実行

```bat
run.bat
```

または:

```bat
.venv\Scripts\activate.bat
python main.py
```

#### 特定タスクのみ実行

```bat
python main.py --task login_bonus
python main.py --task simulation_room
python main.py --task outpost_reward
```

#### 操作記録・再生

```bat
# 操作を記録（F9 で停止）
python main.py --record my_session

# 記録を再生
python main.py --play my_session

# 再生速度を変える（0.5 = 2倍遅く）
python main.py --play my_session --speed 0.5

# 保存済み記録の一覧表示
python main.py --list-recordings
```

#### オプション一覧

```
--task TASK_ID        特定タスクのみ実行
--capture             テンプレートキャプチャモード（スクリーンショット保存）
--debug               デバッグログを有効化
--stop-on-failure     タスク失敗時に後続を中断
--config PATH         設定ファイルのパス指定
--tasks-config PATH   タスク設定ファイルのパス指定
--record NAME         操作を記録して recordings/<NAME>/ に保存
--play NAME           recordings/<NAME>/recording.json を再生
--speed FACTOR        再生速度倍率（--play と併用、デフォルト: 1.0）
--list-recordings     保存済み記録の一覧を表示
```

---

## 操作記録・再生機能

マウス操作とキー入力を記録して後から自動再生できます。  
再生時はテンプレートマッチングで対象UI要素を探し、見つからない場合は記録時の座標にフォールバックします。

**記録の仕組み:**

1. `--record` または GUI の「記録開始」ボタンで録画開始
2. NIKKEでやりたい操作を実際に行う
3. F9キー（または「記録停止」ボタン）で録画終了
4. クリック時の画面から自動でテンプレート画像が切り出されて保存される

**保存先:**

```
recordings/
└── <記録名>/
    ├── recording.json      ← イベントデータ（座標・タイムスタンプ等）
    ├── click_000.png       ← クリック時のスクリーンショット
    ├── click_001.png
    └── templates/
        ├── click_000.png   ← 切り出したテンプレート画像
        └── click_001.png
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
| `recording.stop_key` | 記録停止キー | f9 |
| `recording.template_padding` | テンプレート切り出し時の余白（px） | 30 |
| `playback.allow_fallback` | テンプレート不一致時に座標フォールバックを許可 | true |
| `playback.scale_coords` | ウィンドウサイズ変化時に座標をスケーリング | true |

### config/tasks.yaml

各タスクの `enabled: true/false` で実行のON/OFFを切り替えられます。

---

## 緊急停止

**マウスを画面の左上隅（座標 0,0）に素早く移動させる**と、PyAutoGUIのフェールセーフ機能が働いて即座に停止します。

---

## ディレクトリ構成

```
nikke-automation/
├── main.py                    # CLIエントリーポイント
├── gui_main.py                # GUIエントリーポイント
├── create_icon.py             # アプリアイコン生成スクリプト
├── nikke_automation.spec      # PyInstaller設定
├── installer.iss              # Inno Setupインストーラー設定
├── requirements.txt
├── setup.bat                  # 初回セットアップ
├── run.bat                    # CLI実行ショートカット
├── run_capture.bat            # テンプレートキャプチャモード
├── build.bat                  # 配布用ビルド（PyInstaller + Inno Setup）
├── config/
│   ├── settings.yaml          # 動作設定
│   └── tasks.yaml             # タスク定義
├── core/
│   ├── window.py              # ウィンドウ検出（Win32 API）
│   ├── capture.py             # スクリーンキャプチャ（mss）
│   ├── matcher.py             # テンプレートマッチング（OpenCV）
│   └── controller.py          # マウス・キーボード操作（PyAutoGUI）
├── tasks/
│   ├── base_task.py           # タスク基底クラス
│   ├── login_bonus.py         # ログインボーナスタスク
│   ├── routine_battle.py      # シミュレーション室・前哨基地タスク
│   ├── tribe_tower.py         # 部族タワータスク（未実装）
│   └── task_runner.py         # タスクランナー（YAML駆動）
├── record/
│   ├── models.py              # データモデル（ClickEvent, KeyEvent 等）
│   ├── recorder.py            # 操作記録エンジン（pynput）
│   ├── player.py              # 記録再生エンジン
│   └── template_extractor.py  # クリック位置からテンプレート自動切り出し
├── gui/
│   ├── app.py                 # GUIアプリ本体（customtkinter）
│   └── log_handler.py         # GUIログハンドラー
├── utils/
│   └── logger.py              # ロギング（コンソール+ファイル）
├── assets/
│   ├── icon.ico               # アプリアイコン
│   └── templates/             # テンプレート画像（要登録）
├── recordings/                # 操作記録データ
└── logs/                      # 実行ログ・エラー時スクリーンショット
```

---

## 配布用ビルド

```bat
build.bat
```

以下の手順が自動で実行されます：

1. 依存パッケージのインストール（PyInstaller, Pillow 等）
2. アプリアイコンの生成（`assets/icon.ico`）
3. PyInstaller で実行ファイルをビルド（`dist/NikkeAutomation/NikkeAutomation.exe`）
4. デスクトップ用ショートカットを作成（`dist/NIKKE Automation.lnk`）
5. Inno Setup がインストール済みの場合はインストーラーも生成（`dist/NikkeAutomation_Setup.exe`）

---

## トラブルシューティング

**「NIKKEウィンドウが見つかりません」**  
→ NIKKEを起動してからツールを実行してください。ウィンドウタイトルが変わっている場合は `config/settings.yaml` の `window.title_candidates` を更新してください。ツールは最大3回リトライします。

**「テンプレートが見つかりません」と表示され動かない**  
→ `assets/templates/` に対応する画像が保存されているか確認してください。`run_capture.bat` で画面を撮影し、切り取って登録してください。

**クリックが意図しない場所に当たる**  
→ ゲームのウィンドウサイズ・解像度を変えないようにしてください。`config/settings.yaml` の `matching.default_threshold` を少し下げる（例: 0.75）と認識しやすくなります。

**実行中に止まってしまう**  
→ `--debug` オプションで詳細ログを確認してください。`logs/screenshots/` にエラー時の画面が保存されます。

**操作記録の再生がずれる**  
→ 記録時と同じウィンドウサイズでプレイしてください。`playback.scale_coords: true` でサイズ差は自動補正されますが、大きく異なる場合は再記録を推奨します。

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
        match = self.wait_for("assets/templates/my_button.png", timeout=10.0)
        if not match.found:
            return self.failed("ボタンが見つかりません")
        self._controller.click_match(match)
        return self.success("完了しました")
```

```yaml
# config/tasks.yaml に追記
- id: my_task
  name: "マイタスク"
  enabled: true
  order: 5
  module: tasks.my_task
  class: MyTask
  config:
    my_template: assets/templates/my_button.png
```

---

*本ツールは個人利用を目的としています。ゲームの利用規約を確認の上ご使用ください。*
