# Google Calendar Monthly Worklog

Google Calendar からタイトル完全一致の予定を取得し、指定月の合計稼働時間を集計する CLI です。  
日跨ぎ・月跨ぎ予定は、対象月内に重なる実時間のみ加算します。
デフォルトでは「現在時刻以前」までを集計し、`--include-through-month-end` で月末まで含めます。

## Requirements

- Python 3.9+
- Google Cloud で Calendar API を有効化した OAuth クライアント情報（`credentials.json`）

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`credentials.json` をこのディレクトリに置いてください。

## Usage

```bash
python calendar_worklog.py --month 2026-02 --title "案件A"
```

任意でタイムゾーン指定:

```bash
python calendar_worklog.py --month 2026-02 --title "案件A" --timezone Asia/Tokyo
```

マッチした予定の詳細を表示:

```bash
python calendar_worklog.py --month 2026-02 --title "案件A" --show-matched-events
```

曜日付きで詳細を表示:

```bash
python calendar_worklog.py --month 2026-02 --title "案件A" --show-matched-events --show-weekday
```

月末まで集計:

```bash
python calendar_worklog.py --month 2026-02 --title "案件A" --include-through-month-end
```

## Output example

```text
Month: 2026-02
Aggregation end: 2026-02-14 21:00 JST
Title (exact): 案件A
Matched events: 7
Total hours: 31.50h
```

## Notes

- 終日予定（all-day event）は集計対象外です。
- タイトルは完全一致のみ対象です（部分一致しません）。
- 初回実行時にブラウザ認証が走り、`token.json` が保存されます。
