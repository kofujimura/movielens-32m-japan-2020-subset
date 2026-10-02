# MovieLens 32Mから授業用の小規模データを作る：Codex作業指示書

作成日：2026-10-02

## 1. 目的と実行範囲

このファイルを読むCodexは、以下の仕様に従って取得・抽出スクリプトを実装し、実データを処理し、検証済みの授業用データを作成する。計画の提示だけで終了しない。

映画ごとの平均評価だけでなく、**同一ユーザーが複数作品を評価した履歴**を残し、嗜好の比較、クラスタリング、協調フィルタリング、評価予測に利用できる形にする。

元データの取得、必要なメタデータの取得、ローカルの実装・実行・検証は実施してよい。外部への公開・アップロード、有料サービスの契約、第三者への問い合わせ送信は作業範囲に含めない。既存ファイルを確認し、ユーザーの作業を上書きしない。

この指示書の作成時点では抽出処理は未実施。残る作品数・ユーザー数・評価件数・日本語タイトルの充足率は未知である。実測前に数値を推測して完成結果として示さない。

## 2. 初期条件：曖昧にせず実装する

| 条件 | 初期仕様 |
|---|---|
| 元データ | 固定版MovieLens 32M。latestや旧版に置き換えない |
| 邦画 | Wikidataのcountry of origin（P495）に日本（Q17）が含まれる作品 |
| 国際合作 | 日本を含めば対象。日本単独製作と区別できる列を残す |
| アニメ・短編 | 含める。実写だけ・長編だけという制限は加えない |
| 2020年以降 | 初期版ではMovieLensのタイトル末尾の作品年が2020以上。評価の投稿年ではない |
| ユーザー | 上記対象作品を異なるmovieIdで5作品以上評価しているユーザー |
| 最終評価表 | 上記ユーザーが上記対象作品に付けた評価を全件残す |
| ユーザーID | 元の匿名userIdを維持。同じIDを全出力で一貫して利用 |
| 作品ID | 元のmovieIdを維持 |
| 評価の日時 | 元のtimestampを保持。可読日時はUTCで派生させる |
| 最低作品評価件数 | 初期条件では設定しない |
| ランダムな間引き | 初期版ではしない |

「そのデータを5件以上」は、32M全体で5件以上ではなく、**対象となる2020年以降の邦画の中で5作品以上**を意味する。抽出ユーザーの洋画・2019年以前の評価は初期成果物には入れない。

作品年は日本公開年・製作年と厳密に同義ではない。初期版の名称は「MovieLens作品年2020年以降・日本製作国を含む作品」とし、「2020年以降に日本公開された全邦画」と呼ばない。日本語の題名、日本語の音声、監督の国籍、Animationジャンルだけで邦画と判定しない。

32Mの評価収録は2023年10月12日まで。2024年以降の新しい評価は入っていない。作品年の上限を勝手に追加せず、実際の最小・最大年を報告し、収録終期より先の作品年があれば個別に確認する。

## 3. 作業ディレクトリと実装方針

実行するプロジェクトの作業ルートを基準に、次のように配置する。以下のパスはこの手順内では相対パスであり、最終報告時には実際の絶対パスを示す。

```text
work/movielens32m/
  raw/                    # ZIP、展開した原本、原本README
  metadata_cache/         # Wikidataレスポンス、実行クエリ、取得日時
  scripts/                # 取得・整形・抽出・検証スクリプト
  config.json             # 抽出設定
  metadata_overrides.csv  # 根拠付きの手動補正がある場合のみ
  logs/                   # ログ、照合不能・競合の記録
  requirements.txt        # 実際に使用した依存関係・バージョン
outputs/movielens_jp_2020_min5/
  ratings.csv
  movies.csv
  users.csv
  README.md
  data_dictionary.md
  report.md
  manifest.json
  checksums.sha256
  licenses/
```

Pythonとpandasのチャンク読み込み、またはDuckDB等のディスク上で処理できる方法を使う。32M全件を不要にメモリへ展開しない。元データは変更しない。既存の環境があれば利用し、必要なら作業用仮想環境を作る。依存関係を固定し、再実行コマンドをREADMEに記載する。

処理は、download → metadata → extract → validate → report に分け、取得済みファイルとメタデータキャッシュを再利用して再開できるようにする。具体的なファイル名やコマンドは実装に合わせて確定する。

初期設定例：

```json
{
  "dataset": "ml-32m",
  "min_movie_year": 2020,
  "year_source": "movielens_title_suffix",
  "country_source": "wikidata_P495",
  "country_qid": "Q17",
  "include_coproductions": true,
  "include_animation": true,
  "min_target_movies_per_user": 5,
  "min_ratings_per_movie": null,
  "seed": 42
}
```

## 4. 元データを取得・確認する

公式配布ページ：https://grouplens.org/datasets/movielens/32m/

公式ZIP：https://files.grouplens.org/datasets/movielens/ml-32m.zip

公式README：https://files.grouplens.org/datasets/movielens/ml-32m-README.html

1. 公式ZIPとREADMEを保存し、取得日時・URL・SHA-256を記録する。
2. 正常にダウンロードできたこと、ZIP内のパスが展開先の外に出ないことを確認して展開する。
3. ZIP同梱のREADMEと、公式に提供されるチェックサムを確認する。利用条件に食い違いがある場合は記録し、都合のよい一方だけを採用しない。
4. 必須ファイル `movies.csv`、`links.csv`、`ratings.csv` の列、IDの型、作品IDの一意性を確認する。タグ分析は任意であり、最初の抽出には不要。
5. `movies.csv` の件数と処理時に数えた評価件数を原本説明と照合する。別版・破損が疑われたらそのまま進めない。

公式説明では、評価32,000,204件、作品87,585件、ユーザー200,948人。IDと日時を含むCSVが利用できる。詳細と現在の利用条件は保存したREADMEを正とする。

## 5. 年と製作国を付与する

### 5.1 作品年の候補抽出

`movies.csv` のtitleの**末尾**にある4桁年を、例えば `r"\((\d{4})\)\s*$"` で抽出する。タイトル途中の数字は年として扱わない。年を読めない作品は欠損として別表に保存する。

まず作品年2020以上の候補に絞り、その候補だけ製作国を照合する。年欠損作品を「2020年未満」とみなさない。年欠損の件数と扱いを報告し、自動的な推測補完はしない。

### 5.2 Wikidataで製作国を照合する

MovieLens自体には製作国がないため、`links.csv` のimdbIdとWikidataのIMDb ID（P345）を結ぶ。Wikidataの構造化データはCC0で、認証キーなしの取得経路がある。IMDbのWebサイトをスクレイピングする必要はない。

- imdbIdは文字列として読み込む。数値化して先頭ゼロを失った場合は、数字部分を最低7桁にゼロ埋めして `tt` を付ける。8桁以上は切り捨てない。
- 完全一致する外部IDを用い、題名の類似一致だけで自動確定しない。
- Wikidata Query Service等で候補のIMDb IDを小分けに照合する。最初は50件程度のバッチ、同時実行1、タイムアウト・バックオフ付きとする。これらは実装上の保守的な初期値であり、公式の固定上限ではない。
- 意味のあるUser-Agentを指定する。429ではRetry-Afterに従う。APIの一時的失敗と「正常応答だが一致なし」を区別し、失敗を非邦画と判定しない。
- 応答JSON、送信クエリ、取得日時、取得成功状態をキャッシュする。途中までの照合を完了扱いにしない。
- 初期照合では国を日本に限定せず、照合先・製作国を取得する。そうしないと「非邦画」と「情報欠損」を区別できない。

SPARQLのひな型（VALUESは実際の候補IDに置き換える。未実行の例）：

```sparql
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?imdbId ?item ?country ?titleJa WHERE {
  VALUES ?imdbId { "tt0000000" }
  ?item wdt:P345 ?imdbId .
  OPTIONAL { ?item wdt:P495 ?country . }
  OPTIONAL {
    ?item rdfs:label ?titleJa .
    FILTER(LANG(?titleJa) = "ja")
  }
}
```

利用先：https://query.wikidata.org/sparql

複数国による複数行を、そのまま評価表へ結合してはいけない。作品ごとに国を集合としてまとめ、メタデータを**1 movieIdにつき1行**へ正規化してから結合する。

照合結果は次の状態に分ける：

- `jp_confirmed`：一意な照合先のP495にQ17を含む。
- `other_country`：一意な照合先に国の情報があり、Q17を含まない。あくまで取得時のWikidataに基づく分類。
- `country_missing`：照合先はあるが国が欠損。
- `unmatched`：外部IDがない、または正常に照合しても一致しない。
- `ambiguous`：同一IMDb IDに複数の別作品が対応するなど競合がある。
- `fetch_failed`：通信失敗等で未確認。取得再試行の対象。

`jp_confirmed`だけを初期抽出対象にする。分類件数と欠損率を残し、欠損・未照合による対象作品の取りこぼしがあり得ると説明する。日本語タイトルが欠損の場合は元のタイトルを残し、題名を創作しない。

対象作品が少ない場合は、直ちに年や評価件数の条件を緩めず、まず国情報・ID照合の欠損と誤対応を調べる。必要な個別補正は `metadata_overrides.csv` に元値・補正値・根拠URL・確認日・理由を記録して再現可能にする。別のデータ提供元を追加する場合は、その利用条件と必要な認証を別途確認する。APIキーや有料サービスを勝手に作らない。

P577などの公開日情報を追加取得しても、国別公開日や映画祭上映日を混ぜて単純に最小値を日本公開日としない。初期版の年基準を変更する必要はない。

## 6. 評価とユーザーを絞る

1. 対象作品ID集合Mを確定する。
2. `ratings.csv` をチャンク読み込みまたはDuckDBで走査し、movieIdがMに含まれる行だけを中間ファイルへ出す。この走査で原本の総行数も数える。
3. 対象内でユーザーごとの**異なるmovieIdの数**を数える。
4. 5作品以上評価したユーザーID集合Uを作る。
5. 中間ファイルからuserIdがUに含まれる行をすべて出力する。
6. 最終評価表に登場する作品だけを `movies.csv` に、ユーザーだけを `users.csv` に出す。Mに含まれたが最終的に評価が残らなかった作品は監査用の一覧と件数を残す。

数式では `R_target = {r : r.movieId ∈ M}`、`U = {u : distinct_count(movieId | userId=u, R_target) >= 5}`、`R_final = {r ∈ R_target : r.userId ∈ U}`。

DuckDB等での実装に対応する論理SQL：

```sql
WITH target_ratings AS (
  SELECT r.*
  FROM ratings r
  JOIN target_movies m ON r.movieId = m.movieId
), eligible_users AS (
  SELECT userId
  FROM target_ratings
  GROUP BY userId
  HAVING COUNT(DISTINCT movieId) >= 5
)
SELECT r.*
FROM target_ratings r
JOIN eligible_users u ON r.userId = u.userId
ORDER BY r.userId, r.timestamp, r.movieId;
```

`target_movies`は作品IDが一意であること。userId×movieIdの重複が原本にあれば原因を確認し、黙って最後の1行を残す処理はしない。初期条件に作品側の最低評価数はないため、反復的なk-core抽出は行わない。

## 7. 成果物の内容

### データ表

- `ratings.csv`：`userId, movieId, rating, timestamp, rated_at_utc`。原本の評価点を変更しない。
- `movies.csv`：`movieId, title, title_ja, movie_year, genres, imdb_id, wikidata_qid, country_qids, is_coproduction, metadata_status, metadata_retrieved_at_utc, n_ratings_subset, mean_rating_subset, std_rating_subset`。
- `users.csv`：`userId, n_target_movies, mean_rating_subset, std_rating_subset, first_rating_at_utc, last_rating_at_utc`。集計は最終抽出内のみ。

国とジャンルなどの複数値は区切り規則を固定し、データ辞書に記載する。日本語を含むCSVはUTF-8で保存する。Excel用のBOM付き版が必要なら別ファイル名で出す。標準偏差は標本標準偏差（ddof=1）とし、1件の作品では欠損を0に置き換えない。ユーザーの国籍や居住地を推測して列を追加しない。

### 説明・監査用のファイル

- `README.md`：目的、正確な抽出条件、再実行方法、出典、利用条件、対象期間、限界。
- `data_dictionary.md`：列の意味、型、欠損の表現、日時・複数値の扱い。
- `report.md`：処理段階ごとの件数、欠損・競合、最終件数、ファイルサイズ、下記の分析適性、検証結果。
- `manifest.json`：設定、実行日時、取得URL、原本とメタデータキャッシュのハッシュ、コード・依存関係の版、実行コマンド。再現に必要な手動補正ファイルのハッシュも含める。
- `checksums.sha256`：配布ファイルのハッシュ一覧。自身のハッシュは含めない。
- `licenses/`：MovieLens原本の利用条件と引用情報、WikidataのCC0と出典情報。

調査時点の32M個別READMEには、同じ条件を維持した加工・再配布の許可と、商用・収益目的の別途許可条件がある。実行時に取得した原本と現行条件を確認し、その条件を保つ。**評価データを含む成果物全体をCC0と表示しない。** 製作国等の追加メタデータのライセンスとは分ける。成果物を自動的にWeb公開しない。

## 8. 必須検証とレポート

実データに対する次の検査をコード化し、成功・失敗をレポートに記録する。失敗した成果物を検証済みと呼ばない。

- 最終評価の全movieIdが対象作品で、全userIdが対象ユーザーである。
- 最終表で全ユーザーが異なる対象作品を5作品以上評価している。
- movieIdとuserIdの参照整合性、作品表・ユーザー表の主キー一意性を満たす。
- userId×movieIdが一意であり、評価は0.5〜5.0の0.5刻み。
- 作品年2020以上、確認済みの国集合にQ17を含む。
- 評価行が原本と一致し、結合による件数増殖・合成・改変がない。
- ユーザー別件数・作品別件数の合計が、ともに最終評価件数に一致する。
- timestampのUTC変換が正しく、評価日時が原本の範囲内である。
- キャッシュを固定した再実行で、並び順を固定した主要CSVの内容が一致する。

レポートには以下を含める：

1. 年条件の候補数 → 国照合の状態別件数 → 邦画確定数 → 対象評価数・ユーザー数 → 5作品条件適用後の作品数・ユーザー数・評価件数。
2. 年別・ジャンル別の作品数、アニメ／それ以外の内訳、合作の件数、作品年と評価日時それぞれの最小・最大。
3. ユーザー別評価件数・作品別評価件数の最小、中央値、最大、および評価点の分布。
4. 最終評価行列の密度 `評価件数 / (ユーザー数 × 作品数)`。空集合なら計算不能と明記。
5. 二部グラフの連結成分数と最大成分のユーザー数・作品数。共通評価作品が少なければ、ユーザー間類似度が安定しにくいと説明する。
6. 最も評価件数の多い作品、評価が分かれる作品の候補。分散の順位には集計対象件数を併記し、少数評価による順位の不安定さを説明する。
7. CSV合計の実測サイズ。初期目安として10MB以内なら扱いやすいと評価するが、超えても勝手に切り捨てない。

データが小さすぎる場合も、その結果自体を報告する。年条件2020以上を維持したまま、最低評価作品数3・5・10での残存件数を感度分析として併記してよい。ただし正式成果物は5のままにする。2015年以降へ広げる、日本以外も含める、作品を削るなどの条件変更は提案として示し、変更版を正式版に置き換えない。

ユーザーや作品を追加で間引く必要が生じた場合は、固定seedのユーザー単位抽出を優先し、対象内の各ユーザーの全評価を残す。追加で作品を減らすと5作品条件が崩れるため、最後に必ず再検証する。

## 9. 授業での解釈と分析案

- 対象は「日本映画を評価したMovieLensユーザー」であり、日本人・日本在住者の標本ではない。
- 国情報の欠損による取りこぼしと、対象作品を5作品以上評価するユーザーへの選択を含む。
- 未評価は0点でも嫌いでもない。推薦実験では欠損をそのまま負例と扱わない。
- rating timestampは評価記録の日時であり、実際の鑑賞日時とは限らない。
- 2023年作品は観測期間が短い。年ごとの評価件数を作品の人気だけで説明しない。

授業案は、ユーザーごとの採点の甘辛、平均を引いた評価による嗜好比較、ジャンル別嗜好、共通評価数を考慮した類似ユーザー探索、人気順推薦と協調フィルタリングの比較など。まず抽出データの規模・疎密に合う課題を提案する。

予測実験を作る場合は、ユーザーごとに過去を学習・新しい評価を検証用とする設計を検討する。標準化、平均点、特徴量は学習データだけで計算し、テスト評価を混ぜない。付属のusers.csvやmovies.csvの全体集計列を、そのまま予測特徴量に使わない。5件以上という抽出条件自体も全期間を見た条件なので、抽出後の集団内評価であることを明記する。

## 10. 完了時に伝えること

最終回答では、抽出条件、実測の作品数・ユーザー数・評価数、合計サイズ、代表的な作品、メタデータの未解決件数、検証結果、各成果物へのパス、再実行コマンドを簡潔に報告する。外部取得が止まった場合は、完了済み工程・未完了工程・再開方法を明確にする。途中成果物と完成した教材を混同しない。

## 11. 一次資料

- [MovieLens 32M配布ページ](https://grouplens.org/datasets/movielens/32m/)
- [MovieLens 32M README：仕様・ライセンス・引用情報](https://files.grouplens.org/datasets/movielens/ml-32m-README.html)
- [Wikidata：country of origin / P495](https://www.wikidata.org/wiki/Property:P495)
- [Wikidata：IMDb ID / P345](https://www.wikidata.org/wiki/Property:P345)
- [Wikidata：publication date / P577](https://www.wikidata.org/wiki/Property:P577)
- [Wikidata：データアクセスの方法・利用上の推奨事項](https://www.wikidata.org/wiki/Wikidata:Data_access)
- [Wikidata：ライセンス](https://www.wikidata.org/wiki/Wikidata:Licensing)

## ターミナルのCodexへ渡す指示例

> `outputs/movielens_32m_subset_handoff.md` を読み、仕様に従って実装とデータ抽出を行ってください。まず既存ファイルを確認し、MovieLens 32MとWikidataから「MovieLens作品年2020年以降・日本製作国を含む作品」を特定し、その中で5作品以上を評価したユーザーの対象内評価履歴を残してください。キャッシュと根拠を保存し、再現可能なスクリプト、検証済みCSV、件数・サイズ・欠損率を示すレポートを作ってください。データが少なくても条件を勝手に緩めず、正式条件での結果と改善案を報告してください。
