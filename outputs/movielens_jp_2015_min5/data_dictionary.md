# データ辞書

CSVはUTF-8、カンマ区切り、引用符はCSV標準、欠損は空欄。数値は小数点.、日時はUTC。作品ID・ユーザーIDを再採番しない。標準偏差の空欄を0に置換しない。

## ratings.csv

| 列 | 型 | 意味 |
| --- | --- | --- |
| userId | integer | 原本の匿名ユーザーID。全ファイル共通 |
| movieId | integer | 原本の作品ID。全ファイル共通 |
| rating | number | 原本評価。0.5〜5.0の0.5刻み |
| timestamp | integer | 原本のUNIX秒 |
| rated_at_utc | string | timestampをISO 8601 UTCへ変換。末尾Z |

## movies.csv

| 列 | 型 | 意味 |
| --- | --- | --- |
| movieId | integer | 原本の作品ID。全ファイル共通 |
| title | string | MovieLens原題名（末尾年を保持） |
| title_ja | string/null | Wikidata日本語ラベル。欠損は創作せず空欄。表示時はtitleへフォールバック |
| movie_year | integer | title末尾の括弧内4桁年 |
| genres | string | 原本ジャンル。\|区切り。(no genres listed)は原本の欠損相当表記 |
| imdb_id | string | tt + 数字最低7桁。8桁以上を切り捨てない |
| wikidata_qid | string | 一意な対応作品QID |
| country_qids | string | P495国QID集合。重複除去・文字列昇順・\|区切り |
| is_coproduction | boolean | true/false。取得した国集合が2か国以上ならtrue。欠損国がある可能性は残る |
| metadata_status | string | 正式作品表はjp_confirmedのみ |
| metadata_retrieved_at_utc | string | 対応バッチの取得完了日時。UTC・末尾Z |
| n_ratings_subset | integer | 正式抽出内の作品別評価行数 |
| mean_rating_subset | number | 正式抽出内の算術平均 |
| std_rating_subset | number/null | 正式抽出内の標本標準偏差ddof=1。1件は空欄 |

## users.csv

| 列 | 型 | 意味 |
| --- | --- | --- |
| userId | integer | 原本の匿名ユーザーID。全ファイル共通 |
| n_target_movies | integer | 正式抽出内の異なる対象movieId数 |
| mean_rating_subset | number | 正式抽出内の算術平均 |
| std_rating_subset | number/null | 正式抽出内の標本標準偏差ddof=1。1件は空欄 |
| first_rating_at_utc | string | 抽出内の最初の評価日時UTC |
| last_rating_at_utc | string | 抽出内の最後の評価日時UTC |

監査表metadata_all_candidates.csvは1 movieIdにつき1行。ambiguous行のQID・国集合は複数候補の監査情報であり、対象判定に利用しない。evidence_query_sha256は保存SPARQL本文のSHA-256。unmatchedは外部IDなしまたは正常応答で一致なし、country_missingは一意な照合先の国欠損、fetch_failedは取得失敗を表す。
