# 札幌エリア 物件リノベーション分析ツール

札幌市（西区・北区・手稲区）の一戸建て物件について、購入戦略別の総費用・月額返済・適合スコアを算出するCLIツールです。

## 対応戦略

- **中古一戸建て + リノベーション** — 築年数・状態に応じた工事費を推計
- **土地 + 新築** — 新築工事費（北海道仕様 80万円/坪）を加算
- **新築一戸建て** — 購入価格 + 諸費用のみ

## セットアップ

Python 3.8以上。外部ライブラリ不要。

```bash
git clone https://github.com/shishishi23/sample-repo.git
cd sample-repo
```

## 使い方

```bash
# 基本（サンプルデータで分析）
python analyzer.py data/sample_properties.json

# 予算上限5500万円・スコア順
python analyzer.py data/sample_properties.json --budget 5500 --sort score

# CSV形式で出力
python analyzer.py data/sample_properties.json -f csv -o result.csv

# 特定物件をIDで比較
python analyzer.py data/sample_properties.json --compare PROP-001 PROP-002

# 上位3件のみ表示
python analyzer.py data/sample_properties.json --top 3
```

### オプション一覧

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `-o FILE` | 出力ファイル | stdout |
| `-f {markdown,csv}` | 出力形式 | markdown |
| `--budget MAX` | 総費用上限（万円） | 制限なし |
| `--min-land TSUBO` | 最低土地面積（坪） | 150 |
| `--min-building TSUBO` | 最低建物面積（坪） | 50 |
| `--sort {score,cost,value}` | 並び順 | score |
| `--top N` | 上位N件のみ | 全件 |
| `--compare ID...` | 指定IDのみ詳細比較 | — |

## 物件データ形式（JSON）

```json
[
  {
    "id": "PROP-001",
    "name": "西区山の手 中古一戸建て",
    "property_type": "中古一戸建て",
    "district": "西区",
    "price_man": 3200,
    "land_tsubo": 180,
    "building_tsubo": 55,
    "age_years": 22,
    "condition": "fair",
    "station_minutes": 12,
    "has_outdoor_space": true,
    "school_district_rating": 4,
    "notes": "備考"
  }
]
```

**condition値:** `excellent`（築浅/リフォーム済）/ `good`（良好）/ `fair`（要工事）/ `poor`（大規模工事要）

**district値:** `西区` / `北区` / `手稲区` / `その他`

## テスト実行

```bash
python -m unittest discover tests/
```

## ファイル構成

```
├── analyzer.py          CLIエントリーポイント
├── models.py            データモデル（Property, Score 等）
├── costs.py             リノベ費用・住宅ローン計算エンジン
├── scorer.py            物件スコアリングエンジン
├── report.py            レポート生成（Markdown / CSV）
├── data/
│   └── sample_properties.json  サンプル物件データ（5件）
└── tests/
    └── test_analysis.py         ユニットテスト
```

## 費用計算の前提

- 諸費用: 購入価格の7.5%（仲介手数料・登記・税）
- 住宅ローン: フラット35相当 年1.635%、35年、頭金10%
- 新築工事費: 80万円/坪（北海道仕様断熱込み）
- 外装リノベ: 雪荷重対応で×1.2の係数を適用
