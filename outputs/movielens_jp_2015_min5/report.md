# 抽出・検証レポート

生成日時: 2026-10-04T13:09:18Z。正式条件: MovieLens作品年2015年以降・P495に日本Q17を含む一意照合作品・対象内5作品以上のユーザー。指定年以外の抽出条件は元の仕様を維持。

## 処理段階

| 段階 | 件数 |
| --- | --- |
| 原本作品 | 87585 |
| 原本評価 | 32000204 |
| 原本ユーザー | 200948 |
| 作品年欠損（推測補完せず別表） | 617 |
| 2015年以上候補 | 23766 |
| jp_confirmed | 630 |
| other_country | 18022 |
| country_missing | 160 |
| unmatched | 4947 |
| ambiguous | 7 |
| fetch_failed | 0 |
| 対象作品への全評価 | 39679 |
| 対象内1件以上のユーザー | 17210 |
| 5作品条件後の作品 | 601 |
| 5作品条件後のユーザー | 1771 |
| 5作品条件後の評価 | 16080 |
| 対象だが正式評価が残らない作品 | 29 |

## 照合と欠損

年欠損: 617/87585 (0.70%)。候補のIMDb欠損: 0。未解決: 5114/23766 (21.52%)。未解決は非邦画と同一視しない。手動補正は0件。全候補の照合と根拠キーはlogs_2015/metadata_all_candidates.csv、未解決はlogs_2015/metadata_unresolved.csv。

| 状態 | 候補中の件数 | 候補を分母とする率 |
| --- | --- | --- |
| jp_confirmed | 630 | 2.65% |
| other_country | 18022 | 75.83% |
| country_missing | 160 | 0.67% |
| unmatched | 4947 | 20.82% |
| ambiguous | 7 | 0.03% |
| fetch_failed | 0 | 0.00% |

未解決のうち原本評価件数の多い候補を以下に示す。日本作品の候補と確定した一覧ではなく、照合改善の優先確認先である。題名だけで国を推定せず正式対象へ追加していない。全候補の原本評価件数はlogs_2015/candidate_rating_coverage.csv。

| movieId | 原題名 | 状態 | 原本評価数 | 対応QID |
| --- | --- | --- | --- | --- |
| 263007 | Spider-Man: No Way Home (2021) | ambiguous | 3971 | Q113471777\|Q68934496 |
| 203218 | Good Boys (2019) | unmatched | 571 |  |
| 170357 | Dave Chappelle: The Age of Spin (2017) | unmatched | 403 |  |
| 170729 | Louis C.K. 2017 (2017) | unmatched | 348 |  |
| 183197 | Dave Chappelle: Equanimity (2017) | unmatched | 268 |  |
| 183227 | Dave Chappelle: The Bird Revelation (2017) | unmatched | 232 |  |
| 170411 | Dave Chappelle: Deep in the Heart of Texas (2017) | unmatched | 214 |  |
| 197379 | Don't Hug Me I'm Scared 6 (2016) | unmatched | 183 |  |
| 236995 | Summer Of Soul (…Or, When The Revolution Could Not Be Televised) (2021) | unmatched | 129 |  |
| 280866 | She Said (2022) | unmatched | 114 |  |

複数項目に対応したIMDb IDは各項目の国を合算して日本と判定せず、ambiguousとして保留する。

| movieId | 原題名 | IMDb ID | 競合QID |
| --- | --- | --- | --- |
| 193327 | Best F(r)iends: Volume One (2018) | tt6155194 | Q28132671\|Q90294288 |
| 212018 | Denmark (2019) | tt7037712 | Q130465361\|Q139665844 |
| 214240 | Altered Carbon: Resleeved (2020) | tt9310328 | Q90302055\|Q97230768 |
| 240252 | School-Live! (2019) | tt9038304 | Q17751436\|Q55632686 |
| 258087 | Nila (2016) | tt5082662 | Q138199805\|Q46999829 |
| 263007 | Spider-Man: No Way Home (2021) | tt10872600 | Q113471777\|Q68934496 |
| 288987 | The Last 10 Years (2022) | tt16444750 | Q109360134\|Q112646942 |

競合項目の追加EntityData監査は14記録。P31・P345・P495、ラベル、説明、リビジョンを保存した。同一IMDb IDの複数項目への対応はambiguousのまま除外し、手動補正による追加は行っていない。追加根拠はlogs_2015/ambiguity_entity_audit.jsonおよびmetadata_cache/entity_audit/に保存。

| movieId | 項目（出典リンク） | 日本語ラベル | 項目の説明 |
| --- | --- | --- | --- |
| 193327 | [Q28132671](https://www.wikidata.org/wiki/Special:EntityData/Q28132671.json) | ベスト・悪友 | 2018年の映画 |
| 193327 | [Q90294288](https://www.wikidata.org/wiki/Special:EntityData/Q90294288.json) |  | 2018 film directed by Justin MacGregor |
| 212018 | [Q130465361](https://www.wikidata.org/wiki/Special:EntityData/Q130465361.json) |  | 2019 film |
| 212018 | [Q139665844](https://www.wikidata.org/wiki/Special:EntityData/Q139665844.json) |  | 2020 British film |
| 214240 | [Q90302055](https://www.wikidata.org/wiki/Special:EntityData/Q90302055.json) | オルタード・カーボン：リスリーブド | 2020 animated film directed by Takeru Nakajima and Yoshiyuki Okada |
| 214240 | [Q97230768](https://www.wikidata.org/wiki/Special:EntityData/Q97230768.json) | オルタード・カーボン：リスリーブド | 記載なし |
| 240252 | [Q17751436](https://www.wikidata.org/wiki/Special:EntityData/Q17751436.json) | がっこうぐらし! | 日本の漫画・アニメ作品 |
| 240252 | [Q55632686](https://www.wikidata.org/wiki/Special:EntityData/Q55632686.json) | がっこうぐらし! | 2019 film by Issei Shibata |
| 258087 | [Q138199805](https://www.wikidata.org/wiki/Special:EntityData/Q138199805.json) |  | 2015 Indian film |
| 258087 | [Q46999829](https://www.wikidata.org/wiki/Special:EntityData/Q46999829.json) | Nila/ニラ | 2016 film by Selvamani Selvaraj |
| 263007 | [Q113471777](https://www.wikidata.org/wiki/Special:EntityData/Q113471777.json) | スパイダーマン：ノー・ウェイ・ホーム　THE MORE FUN STUFF VERSION | 2021 film directed by Jon Watts |
| 263007 | [Q68934496](https://www.wikidata.org/wiki/Special:EntityData/Q68934496.json) | スパイダーマン：ノー・ウェイ・ホーム | 2021年のアメリカのスーパーヒーロー映画 |
| 288987 | [Q109360134](https://www.wikidata.org/wiki/Special:EntityData/Q109360134.json) | 余命10年 | 日本の小説、メディアミックス作品 |
| 288987 | [Q112646942](https://www.wikidata.org/wiki/Special:EntityData/Q112646942.json) | 余命10年 | 2022 film directed by Michihito Fujii |

正式CSVの全列について空欄率を示す。ジャンルの(no genres listed)は空欄率に含まないため別記する。

| CSV | 列 | 欠損/行数 | 欠損率 |
| --- | --- | --- | --- |
| ratings.csv | userId | 0/16080 | 0.00% |
| ratings.csv | movieId | 0/16080 | 0.00% |
| ratings.csv | rating | 0/16080 | 0.00% |
| ratings.csv | timestamp | 0/16080 | 0.00% |
| ratings.csv | rated_at_utc | 0/16080 | 0.00% |
| movies.csv | movieId | 0/601 | 0.00% |
| movies.csv | title | 0/601 | 0.00% |
| movies.csv | title_ja | 9/601 | 1.50% |
| movies.csv | movie_year | 0/601 | 0.00% |
| movies.csv | genres | 0/601 | 0.00% |
| movies.csv | imdb_id | 0/601 | 0.00% |
| movies.csv | wikidata_qid | 0/601 | 0.00% |
| movies.csv | country_qids | 0/601 | 0.00% |
| movies.csv | is_coproduction | 0/601 | 0.00% |
| movies.csv | metadata_status | 0/601 | 0.00% |
| movies.csv | metadata_retrieved_at_utc | 0/601 | 0.00% |
| movies.csv | n_ratings_subset | 0/601 | 0.00% |
| movies.csv | mean_rating_subset | 0/601 | 0.00% |
| movies.csv | std_rating_subset | 166/601 | 27.62% |
| users.csv | userId | 0/1771 | 0.00% |
| users.csv | n_target_movies | 0/1771 | 0.00% |
| users.csv | mean_rating_subset | 0/1771 | 0.00% |
| users.csv | std_rating_subset | 0/1771 | 0.00% |
| users.csv | first_rating_at_utc | 0/1771 | 0.00% |
| users.csv | last_rating_at_utc | 0/1771 | 0.00% |

ジャンル未登録: 16作品。日本語タイトル欠損時も原題名titleを保持。国情報の欠落・誤りにより取りこぼしがあり、全邦画の網羅表ではない。

## 作品構成と期間

以下の内訳は正式CSV内の作品数。ジャンルは複数計上されるため合計は作品数を超える。

| 作品年 | 作品数 |
| --- | --- |
| 2015 | 73 |
| 2016 | 86 |
| 2017 | 94 |
| 2018 | 81 |
| 2019 | 81 |
| 2020 | 61 |
| 2021 | 62 |
| 2022 | 48 |
| 2023 | 15 |

| ジャンル | 作品数 |
| --- | --- |
| (no genres listed) | 16 |
| Action | 144 |
| Adventure | 76 |
| Animation | 205 |
| Children | 27 |
| Comedy | 130 |
| Crime | 33 |
| Documentary | 17 |
| Drama | 284 |
| Fantasy | 104 |
| Horror | 40 |
| Mystery | 61 |
| Romance | 84 |
| Sci-Fi | 73 |
| Thriller | 47 |
| War | 13 |
| Western | 1 |

Animationあり 205作品、それ以外 396作品。日本を含む複数国 66作品、取得国集合が日本のみ 535作品。Animationなしを実写確定とは解釈しない。

合作を含む条件により、WikidataのP495に日本がある『ブレット・トレイン』『NOPE/ノープ』『ソニック・ザ・ムービー』等も対象。合作への評価は正式抽出内で6533件。各作品の取得国集合をmovies.csvで確認できる。

正式作品年: 2015〜2023。候補作品年: 2015〜2023。原本評価: 1995-01-09T11:46:44Z〜2023-10-13T02:29:07Z。正式評価: 2015-08-16T14:28:56Z〜2023-10-13T01:03:51Z。

原本READMEは収録終期を2023年10月12日と説明するが、UTC実測の最大timestampは2023年10月13日02:29:07。収録終期表記のタイムゾーンは確認できない。公式チェックサムは一致しており、別版と置き換えたり、12日を超えるUTC評価を切り捨てたりせず、この差を記録する。

収録終了年より先の候補作品年: 0作品。logs_2015/years_after_collection_end.csvに記録。年上限フィルタは追加していない。

## 分布と分析適性

| 評価件数 | 最小 | 中央値 | 最大 |
| --- | --- | --- | --- |
| ユーザー別 | 5 | 7 | 174 |
| 作品別 | 1 | 3 | 1314 |

| 評価点 | 件数 |
| --- | --- |
| 0.5 | 415 |
| 1.0 | 338 |
| 1.5 | 344 |
| 2.0 | 811 |
| 2.5 | 1189 |
| 3.0 | 2600 |
| 3.5 | 3465 |
| 4.0 | 3700 |
| 4.5 | 1807 |
| 5.0 | 1411 |

行列密度: 1.5108%。
二部グラフの連結成分: 1。最大成分: 1771ユーザー・601作品。連結していても各ユーザー対の共通評価が十分とは限らず、共通評価数の少ない類似度は不安定。

16,080評価を含む。件数と疎密を確認する導入演習、採点の甘辛、ユーザー平均を引いた嗜好比較に利用できる。作品の166件は評価1件で、標本標準偏差を計算できない。推薦実験は人気順・平均点の基準モデルから始め、共通評価数を併記した類似度を使う。評価数の少ない作品の予測と分散推定は不安定。分割後の各ユーザーの学習件数を確認し、時系列分割で情報漏洩を防ぐ。全期間集計列を予測特徴量に直接使わない。

| 作品ペアの共通評価者数 | ペア数 |
| --- | --- |
| 全作品ペア | 180300 |
| 0人 | 144367 |
| 1人以上 | 35933 |
| 2人以上 | 12436 |
| 3人以上 | 7339 |
| 5人以上 | 3965 |
| 10人以上 | 1680 |
| 20人以上 | 715 |

年を広げて評価件数が増えても、作品数・ユーザー数も増えるため密度が上がるとは限らない。作品類似度の分析では共通評価者数と未推定ペアを併記し、未評価を0点で埋めない。

## 評価件数の多い作品

| movieId | 作品 | 件数 | 平均 | 標本標準偏差 |
| --- | --- | --- | --- | --- |
| 168250 | ゲット・アウト | 1314 | 3.848 | 0.820 |
| 163134 | 君の名は。 | 1080 | 4.041 | 0.847 |
| 200838 | 名探偵ピカチュウ | 606 | 3.125 | 0.858 |
| 275245 | NOPE/ノープ | 560 | 3.508 | 0.886 |
| 188773 | 万引き家族 | 552 | 3.945 | 0.790 |
| 273891 | ブレット・トレイン | 510 | 3.458 | 0.872 |
| 188623 | バーニング 劇場版 | 507 | 3.738 | 0.908 |
| 166291 | 映画 聲の形 | 490 | 3.859 | 0.916 |
| 200820 | ゴジラ:キング・オブ・ザ・モンスターズ | 483 | 2.763 | 1.031 |
| 143367 | 沈黙 | 416 | 3.500 | 0.926 |

## 評価が分かれる候補

標本標準偏差の降順（分散と同じ順位）。2件以上の作品を掲載。少数評価で高順位になりやすく、安定した賛否の証拠ではない。

| movieId | 作品 | 件数 | 標本標準偏差 |
| --- | --- | --- | --- |
| 203747 | ハナレイ・ベイ | 2 | 2.828 |
| 220908 | Berlin Drifters (2017) | 2 | 2.828 |
| 279806 | 劇場版 進撃の巨人 Season2 覚醒の咆哮 | 2 | 2.828 |
| 207826 | あした世界が終わるとしても | 3 | 2.255 |
| 186593 | 毛虫のボロ | 3 | 2.179 |
| 203733 | 人魚の眠る家 | 2 | 2.121 |
| 205765 | 少女椿 | 2 | 2.121 |
| 267380 | 映画 賭󠄀ケグルイ | 2 | 2.121 |
| 267500 | 東京リベンジャーズ | 2 | 2.121 |
| 279376 | さがす | 2 | 2.121 |

## 感度分析と改善案

作品年2015以上と日本条件は固定。下表は比較集計のみで、正式CSVは5作品条件を維持。

| 最低作品数 | 作品 | ユーザー | 評価 |
| --- | --- | --- | --- |
| 3 | 617 | 3930 | 23338 |
| 5 | 601 | 1771 | 16080 |
| 10 | 575 | 494 | 8050 |

改善はまず未照合・国欠損・複数候補の個別確認を行い、補正する場合は元値・補正値・根拠URL・確認日・理由をmetadata_overrides.csvへ保存する。日本語題名や監督国籍だけで日本作品にしない。次の別条件実験として最低3作品や他国を含む比較を検討できるが、この版には適用していない。MovieLensの2023年10月までという観測終期は変更できず、最近の作品ほど評価蓄積が少ない。

## ファイルサイズ

| ファイル | bytes |
| --- | --- |
| ratings.csv | 795052 |
| movies.csv | 108522 |
| users.csv | 142002 |
| 合計 | 1045576 |

合計 1.046 MB (10進)、0.997 MiB。10 MB以内で授業用に扱いやすいサイズ。

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
| all_2020_final_ratings_preserved_in_2015 | 成功 |
| all_2020_metadata_and_retrieval_timestamps_preserved | 成功 |
| frozen_response_cache_rebuilds_identical_metadata | 成功 |
| frozen_cache_replay_sha256_ratings.csv | 成功 |
| frozen_cache_replay_sha256_movies.csv | 成功 |
| frozen_cache_replay_sha256_users.csv | 成功 |

原本ZIPの公式MD5、各CSVの公式MD5、ZIP CRCと展開パスを確認。32,000,204評価を逐次走査し、原本全体のID参照・評価値・userId×movieId一意性を確認。別走査で対象ユーザー集合と全評価の原本一致を検証。固定レスポンスキャッシュからメタデータを再構築し、3つのCSVのSHA-256一致を確認。詳細はlogs_2015/validation.json。

## 出典・利用条件

[MovieLens 32M](https://grouplens.org/datasets/movielens/32m/)、[原本README](https://files.grouplens.org/datasets/movielens/ml-32m-README.html)、[Wikidata P495](https://www.wikidata.org/wiki/Property:P495)、[P345](https://www.wikidata.org/wiki/Property:P345)。
MovieLens同梱READMEと公式HTML READMEの主要条件に矛盾なし。全文をlicenses/に保存。Wikidataの構造化追加データのみCC0。評価データを含む成果物全体はCC0ではない。コード用MITライセンスはデータ・統計・レポートには適用されない。公開・再配布時も原本の利用条件・出典を維持する。
