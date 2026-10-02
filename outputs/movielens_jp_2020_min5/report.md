# 抽出・検証レポート

生成日時: 2026-10-02T06:25:37Z。正式条件: MovieLens作品年2020年以降・P495に日本Q17を含む一意照合作品・対象内5作品以上のユーザー。条件変更なし。

## 処理段階

| 段階 | 件数 |
| --- | --- |
| 原本作品 | 87585 |
| 原本評価 | 32000204 |
| 原本ユーザー | 200948 |
| 作品年欠損（推測補完せず別表） | 617 |
| 2020年以上候補 | 7986 |
| jp_confirmed | 196 |
| other_country | 5973 |
| country_missing | 53 |
| unmatched | 1761 |
| ambiguous | 3 |
| fetch_failed | 0 |
| 対象作品への全評価 | 6476 |
| 対象内1件以上のユーザー | 3792 |
| 5作品条件後の作品 | 159 |
| 5作品条件後のユーザー | 176 |
| 5作品条件後の評価 | 1177 |
| 対象だが正式評価が残らない作品 | 37 |

## 照合と欠損

年欠損: 617/87585 (0.70%)。候補のIMDb欠損: 0。未解決: 1817/7986 (22.75%)。未解決は非邦画と同一視しない。手動補正は0件。全候補の照合と根拠キーはlogs/metadata_all_candidates.csv、未解決はlogs/metadata_unresolved.csv。

| 状態 | 候補中の件数 | 候補を分母とする率 |
| --- | --- | --- |
| jp_confirmed | 196 | 2.45% |
| other_country | 5973 | 74.79% |
| country_missing | 53 | 0.66% |
| unmatched | 1761 | 22.05% |
| ambiguous | 3 | 0.04% |
| fetch_failed | 0 | 0.00% |

未解決のうち原本評価件数の多い候補を以下に示す。日本作品の候補と確定した一覧ではなく、照合改善の優先確認先である。題名だけで国を推定せず正式対象へ追加していない。全候補の原本評価件数はlogs/candidate_rating_coverage.csv。

| movieId | 原題名 | 状態 | 原本評価数 | 対応QID |
| --- | --- | --- | --- | --- |
| 263007 | Spider-Man: No Way Home (2021) | ambiguous | 3971 | Q113471777\|Q68934496 |
| 236995 | Summer Of Soul (…Or, When The Revolution Could Not Be Televised) (2021) | unmatched | 129 |  |
| 280866 | She Said (2022) | unmatched | 114 |  |
| 213668 | Taylor Tomlinson: Quarter-Life Crisis (2020) | unmatched | 79 |  |
| 214240 | Altered Carbon: Resleeved (2020) | ambiguous | 67 | Q90302055\|Q97230768 |
| 214698 | Tom Segura: Ball Hog (2020) | unmatched | 50 |  |
| 284747 | Chris Rock: Selective Outrage (2023) | unmatched | 49 |  |
| 217079 | Patton Oswalt: I Love Everything (2020) | unmatched | 46 |  |
| 276687 | Bill Burr: Live at Red Rocks (2022) | unmatched | 46 |  |
| 219669 | Jim Jefferies: Intolerant (2020) | unmatched | 43 |  |

複数項目に対応したIMDb IDは各項目の国を合算して日本と判定せず、ambiguousとして保留する。

| movieId | 原題名 | IMDb ID | 競合QID |
| --- | --- | --- | --- |
| 214240 | Altered Carbon: Resleeved (2020) | tt9310328 | Q90302055\|Q97230768 |
| 263007 | Spider-Man: No Way Home (2021) | tt10872600 | Q113471777\|Q68934496 |
| 288987 | The Last 10 Years (2022) | tt16444750 | Q109360134\|Q112646942 |

競合6項目の完全なEntityData JSONも追加取得し、P31・P345・P495、ラベル、説明、リビジョンを確認した。『オルタード・カーボン：リスリーブド』は同じ題名・IMDb IDを持つ2項目、『余命10年』は小説を説明する項目と映画項目が同じIMDb IDを持つ。後者は映画Q112646942への根拠付き補正を検討できる。Spider-Manは通常版と別編集版の項目が同じIMDb IDを共有する。今回の正式版は全3作品をambiguousのまま除外し、補正による追加は行っていない。追加根拠はlogs/ambiguity_entity_audit.jsonおよびmetadata_cache/entity_audit/に保存。

| movieId | 項目（出典リンク） | 日本語ラベル | 項目の説明 |
| --- | --- | --- | --- |
| 214240 | [Q90302055](https://www.wikidata.org/wiki/Special:EntityData/Q90302055.json) | オルタード・カーボン：リスリーブド | 2020 animated film directed by Takeru Nakajima and Yoshiyuki Okada |
| 214240 | [Q97230768](https://www.wikidata.org/wiki/Special:EntityData/Q97230768.json) | オルタード・カーボン：リスリーブド | 記載なし |
| 263007 | [Q113471777](https://www.wikidata.org/wiki/Special:EntityData/Q113471777.json) | スパイダーマン：ノー・ウェイ・ホーム　THE MORE FUN STUFF VERSION | 2021 film directed by Jon Watts |
| 263007 | [Q68934496](https://www.wikidata.org/wiki/Special:EntityData/Q68934496.json) | スパイダーマン：ノー・ウェイ・ホーム | 2021年のアメリカのスーパーヒーロー映画 |
| 288987 | [Q109360134](https://www.wikidata.org/wiki/Special:EntityData/Q109360134.json) | 余命10年 | 日本の小説、メディアミックス作品 |
| 288987 | [Q112646942](https://www.wikidata.org/wiki/Special:EntityData/Q112646942.json) | 余命10年 | 2022 film directed by Michihito Fujii |

正式CSVの全列について空欄率を示す。ジャンルの(no genres listed)は空欄率に含まないため別記する。

| CSV | 列 | 欠損/行数 | 欠損率 |
| --- | --- | --- | --- |
| ratings.csv | userId | 0/1177 | 0.00% |
| ratings.csv | movieId | 0/1177 | 0.00% |
| ratings.csv | rating | 0/1177 | 0.00% |
| ratings.csv | timestamp | 0/1177 | 0.00% |
| ratings.csv | rated_at_utc | 0/1177 | 0.00% |
| movies.csv | movieId | 0/159 | 0.00% |
| movies.csv | title | 0/159 | 0.00% |
| movies.csv | title_ja | 2/159 | 1.26% |
| movies.csv | movie_year | 0/159 | 0.00% |
| movies.csv | genres | 0/159 | 0.00% |
| movies.csv | imdb_id | 0/159 | 0.00% |
| movies.csv | wikidata_qid | 0/159 | 0.00% |
| movies.csv | country_qids | 0/159 | 0.00% |
| movies.csv | is_coproduction | 0/159 | 0.00% |
| movies.csv | metadata_status | 0/159 | 0.00% |
| movies.csv | metadata_retrieved_at_utc | 0/159 | 0.00% |
| movies.csv | n_ratings_subset | 0/159 | 0.00% |
| movies.csv | mean_rating_subset | 0/159 | 0.00% |
| movies.csv | std_rating_subset | 59/159 | 37.11% |
| users.csv | userId | 0/176 | 0.00% |
| users.csv | n_target_movies | 0/176 | 0.00% |
| users.csv | mean_rating_subset | 0/176 | 0.00% |
| users.csv | std_rating_subset | 0/176 | 0.00% |
| users.csv | first_rating_at_utc | 0/176 | 0.00% |
| users.csv | last_rating_at_utc | 0/176 | 0.00% |

ジャンル未登録: 3作品。日本語タイトル欠損時も原題名titleを保持。国情報の欠落・誤りにより取りこぼしがあり、全邦画の網羅表ではない。

## 作品構成と期間

以下の内訳は正式CSV内の作品数。ジャンルは複数計上されるため合計は作品数を超える。

| 作品年 | 作品数 |
| --- | --- |
| 2020 | 53 |
| 2021 | 51 |
| 2022 | 41 |
| 2023 | 14 |

| ジャンル | 作品数 |
| --- | --- |
| (no genres listed) | 3 |
| Action | 46 |
| Adventure | 29 |
| Animation | 68 |
| Children | 9 |
| Comedy | 35 |
| Crime | 10 |
| Documentary | 4 |
| Drama | 87 |
| Fantasy | 38 |
| Horror | 7 |
| Mystery | 17 |
| Romance | 27 |
| Sci-Fi | 24 |
| Thriller | 15 |
| War | 1 |
| Western | 1 |

Animationあり 68作品、それ以外 91作品。日本を含む複数国 17作品、取得国集合が日本のみ 142作品。Animationなしを実写確定とは解釈しない。

合作を含む条件により、WikidataのP495に日本がある『ブレット・トレイン』『NOPE/ノープ』『ソニック・ザ・ムービー』等も対象。合作への評価は正式抽出内で402件。各作品の取得国集合をmovies.csvで確認できる。

正式作品年: 2020〜2023。候補作品年: 2020〜2023。原本評価: 1995-01-09T11:46:44Z〜2023-10-13T02:29:07Z。正式評価: 2020-02-14T04:33:19Z〜2023-10-11T08:29:56Z。

原本READMEは収録終期を2023年10月12日と説明するが、UTC実測の最大timestampは2023年10月13日02:29:07。収録終期表記のタイムゾーンは確認できない。公式チェックサムは一致しており、別版と置き換えたり、12日を超えるUTC評価を切り捨てたりせず、この差を記録する。

収録終了年より先の候補作品年: 0作品。logs/years_after_collection_end.csvに記録。年上限フィルタは追加していない。

## 分布と分析適性

| 評価件数 | 最小 | 中央値 | 最大 |
| --- | --- | --- | --- |
| ユーザー別 | 5 | 6.0 | 21 |
| 作品別 | 1 | 3 | 108 |

| 評価点 | 件数 |
| --- | --- |
| 0.5 | 43 |
| 1.0 | 17 |
| 1.5 | 40 |
| 2.0 | 84 |
| 2.5 | 106 |
| 3.0 | 226 |
| 3.5 | 288 |
| 4.0 | 219 |
| 4.5 | 104 |
| 5.0 | 50 |

行列密度: 4.2060%。
二部グラフの連結成分: 1。最大成分: 176ユーザー・159作品。連結していても各ユーザー対の共通評価が十分とは限らず、共通評価数の少ない類似度は不安定。

1,177評価の小規模な教材であり、大規模な推薦精度ベンチマークには向かない。件数と疎密を確認する導入演習、採点の甘辛、ユーザー平均を引いた嗜好比較に利用できる。作品の59件は評価1件で、標本標準偏差を計算できない。推薦実験は人気順・平均点の基準モデルから始め、共通評価数を併記した類似度を使う。評価数の少ない作品の予測と分散推定は不安定。分割後の各ユーザーの学習件数を確認し、時系列分割で情報漏洩を防ぐ。全期間集計列を予測特徴量に直接使わない。

## 評価件数の多い作品

| movieId | 作品 | 件数 | 平均 | 標本標準偏差 |
| --- | --- | --- | --- | --- |
| 273891 | ブレット・トレイン | 108 | 3.319 | 0.882 |
| 275245 | NOPE/ノープ | 105 | 3.514 | 0.908 |
| 210577 | ソニック・ザ・ムービー | 81 | 2.790 | 0.817 |
| 257037 | ドライブ・マイ・カー | 68 | 3.515 | 1.093 |
| 231413 | 劇場版 鬼滅の刃 無限列車編 | 48 | 3.594 | 1.009 |
| 252932 | 竜とそばかすの姫 | 39 | 3.346 | 0.961 |
| 246604 | シン・エヴァンゲリオン劇場版𝄇 | 36 | 3.750 | 1.079 |
| 272079 | 劇場版 呪術廻戦 0 | 35 | 3.214 | 1.262 |
| 281188 | すずめの戸締まり | 34 | 3.618 | 0.697 |
| 253332 | アネット | 31 | 2.935 | 1.047 |

## 評価が分かれる候補

標本標準偏差の降順（分散と同じ順位）。2件以上の作品を掲載。少数評価で高順位になりやすく、安定した賛否の証拠ではない。

| movieId | 作品 | 件数 | 標本標準偏差 |
| --- | --- | --- | --- |
| 279376 | さがす | 2 | 2.121 |
| 277778 | 劇場版 仮面ライダーリバイス バトルファミリア | 2 | 1.768 |
| 287737 | シン・仮面ライダー | 3 | 1.443 |
| 223570 | 劇場版メイドインアビス 深き魂の黎明 | 13 | 1.431 |
| 228401 | カイジ ファイナルゲーム | 2 | 1.414 |
| 244120 | STAND BY ME ドラえもん 2 | 2 | 1.414 |
| 250832 | 名探偵コナン 緋色の弾丸 | 2 | 1.414 |
| 262113 | ブライト: サムライソウル﻿ | 2 | 1.414 |
| 252308 | るろうに剣心 最終章 The Final | 11 | 1.393 |
| 288209 | 映画 ブラッククローバー 魔法帝の剣 | 4 | 1.323 |

## 感度分析と改善案

作品年2020以上と日本条件は固定。下表は比較集計のみで、正式CSVは5作品条件を維持。

| 最低作品数 | 作品 | ユーザー | 評価 |
| --- | --- | --- | --- |
| 3 | 174 | 561 | 2450 |
| 5 | 159 | 176 | 1177 |
| 10 | 91 | 17 | 218 |

改善はまず未照合・国欠損・複数候補の個別確認を行い、補正する場合は元値・補正値・根拠URL・確認日・理由をmetadata_overrides.csvへ保存する。日本語題名や監督国籍だけで日本作品にしない。次の別条件実験として最低3作品、2015年以降、他国を含む比較を検討できるが、今回の正式版へは適用していない。MovieLensの2023年10月までという観測終期は変更できず、最近の作品ほど評価蓄積が少ない。

## ファイルサイズ

| ファイル | bytes |
| --- | --- |
| ratings.csv | 58210 |
| movies.csv | 29048 |
| users.csv | 14003 |
| 合計 | 101261 |

合計 0.101 MB (10進)、0.097 MiB。10 MB以内で授業用に扱いやすいサイズ。

## 検証

| 検査 | 結果 |
| --- | --- |
| primary_keys_unique | 成功 |
| reference_integrity_exact_no_unused_rows | 成功 |
| all_users_at_least_5_distinct_target_movies | 成功 |
| year_and_country_criteria | 成功 |
| rating_domain | 成功 |
| final_user_movie_unique | 成功 |
| utc_conversion_and_source_bounds | 成功 |
| metadata_matches_evidence | 成功 |
| user_count_sum | 成功 |
| movie_count_sum | 成功 |
| all_aggregates_independently_recomputed_ddof1 | 成功 |
| stable_sort_order | 成功 |
| independent_source_count | 成功 |
| eligible_user_set_exact_from_original | 成功 |
| every_final_rating_exact_original_and_all_eligible_rows_retained | 成功 |
| frozen_response_cache_rebuilds_identical_metadata | 成功 |
| frozen_cache_replay_sha256_ratings.csv | 成功 |
| frozen_cache_replay_sha256_movies.csv | 成功 |
| frozen_cache_replay_sha256_users.csv | 成功 |

原本ZIPの公式MD5、各CSVの公式MD5、ZIP CRCと展開パスを確認。32,000,204評価を逐次走査し、原本全体のID参照・評価値・userId×movieId一意性を確認。別走査で対象ユーザー集合と全評価の原本一致を検証。固定レスポンスキャッシュからメタデータを再構築し、3つのCSVのSHA-256一致を確認。詳細はlogs/validation.json。

## 出典・利用条件

[MovieLens 32M](https://grouplens.org/datasets/movielens/32m/)、[原本README](https://files.grouplens.org/datasets/movielens/ml-32m-README.html)、[Wikidata P495](https://www.wikidata.org/wiki/Property:P495)、[P345](https://www.wikidata.org/wiki/Property:P345)。
MovieLens同梱READMEと公式HTML READMEの主要条件に矛盾なし。全文をlicenses/に保存。Wikidataの構造化追加データのみCC0。評価データを含む成果物全体はCC0ではない。コード用MITライセンスはデータ・統計・レポートには適用されない。公開・再配布時も原本の利用条件・出典を維持する。
