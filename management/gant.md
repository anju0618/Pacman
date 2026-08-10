2026
0806 amakino enums.py game_state.py maze_loader.py作成
0806 takawaka 書いて！！後でAIにまとめさせよう！！
0807 amakino バグ修正、configデータ格納　キャラクタのbasemodell class開始
0808 amakino blinkyとかpacmanのクラス作ってて、順番違うなって気づいて中断。グラッフィック開始。　config.jsonのコメントアウト全対応を試みる(reを使用)
0808 amakino Claude Codeにレビューさせてバグ一斉修正。ghoast.pyのNameError、blinky未実装、テスト崩壊、config.livesデフォルト不整合、コメント除去の文字列破壊、config検証の全滅フォールバック、パックマン初期位置が真ん中じゃない、壁にめり込む表示バグ(当たり判定と描画の半径不一致)など。flake8/mypy/pytest全部通るようになった。


```mermaid
gantt
    title Packman Project Timeline - Member Work Division & Tasks
    dateFormat  YYYY-MM-DD
    
    section Anjou Makino (amakino)
    Project Setup (uv, toml, Makefile) :done, a1, 2026-08-06, 2026-08-06
    Specification & Research           :done, a2, 2026-08-06, 2026-08-06
    Enums & Game State Implementation  :done, a3, 2026-08-06, 2026-08-06
    Maze Loader & Test Suite           :done, a4, 2026-08-06, 2026-08-06
    Player Movement & Collision        :        a5, 2026-08-07, 2026-08-10
    Ghost AI & Behavior Logic          :        a6, 2026-08-10, 2026-08-14
    Level Progression & Rules          :        a7, 2026-08-13, 2026-08-16

    section Taiyo Kawakami (takawaka)
    Config Parser (JSON w/ comments)   :active, t1, 2026-08-06, 2026-08-07
    Config Validation & Fallback       :active, t2, 2026-08-06, 2026-08-07
    Highscore System (Persistence)     :        t3, 2026-08-08, 2026-08-11
    Cheat Mode Implementation          :        t4, 2026-08-12, 2026-08-14

    section Collaborative / Both
    Graphic Library & Window Setup     :        j1, 2026-08-08, 2026-08-11
    Game Loop & UI/HUD Integration     :        j2, 2026-08-12, 2026-08-16
    Testing, README & Packaging        :        j3, 2026-08-15, 2026-08-19
```