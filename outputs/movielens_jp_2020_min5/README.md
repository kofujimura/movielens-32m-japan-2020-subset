# MovieLens作品年2020年以降・日本製作国を含む作品

元データは固定版ml-32m。title末尾の4桁年が2020以上、IMDb ID完全一致で一意に対応したWikidataのP495にQ17を含む作品を対象とする。その対象内で異なるmovieIdを5作品以上評価したユーザーの対象内評価を全件残す。合作・アニメ・短編を含む。作品側の最低評価数、年上限、ランダム間引きは設けない。元の匿名userId/movieId、rating、timestampを維持する。

正式成果物は159作品・176ユーザー・1,177評価。CSV合計101,261 bytes。評価表はuserId、timestamp、movieIdの昇順。作品表とユーザー表は各ID昇順。UTF-8、BOMなし、LF改行。

## 再実行

コマンドはこのリポジトリのルートで実行する。Python 3.13.7の標準ライブラリのみ。依存追加は不要。

```sh
python3 work/movielens32m/scripts/pipeline.py download
python3 work/movielens32m/scripts/pipeline.py metadata
python3 work/movielens32m/scripts/pipeline.py extract
python3 work/movielens32m/scripts/pipeline.py validate
python3 work/movielens32m/scripts/pipeline.py report
```

GitHubの公開版にはraw/を含めない。初回は上記downloadで公式原本を取得する。その後、固定キャッシュで全工程を再実行: `python3 work/movielens32m/scripts/pipeline.py all --offline`。
競合の追加監査を含める場合は `python3 work/movielens32m/scripts/pipeline.py metadata --audit-ambiguities --offline`。キャッシュがない初回は--offlineを外す。監査は選定結果を変更しない。回帰テスト: `python3 -m unittest discover -s work/movielens32m/scripts -p 'test_*.py' -v`。
downloadの再利用時も原本チェックサムを検証する。通信失敗はfetch_failedとして記録し、metadataを再実行すれば成功済みバッチを再利用する。失敗が残れば抽出を停止する。キャッシュ取得時刻も固定するため主要CSVはバイト単位で再現する。レポート・manifestの実行時刻は更新される。

原本は `work/movielens32m/raw/`、クエリ・JSON応答・HTTP取得情報は `metadata_cache/`、候補全件・欠損年・未解決照合・最終評価が残らなかった対象作品は `logs/`。候補表のevidence_query_sha256から同名の.rqと.jsonを参照できる。手動補正は行っていない。キャッシュ固定が再現の前提であり、将来新規にWikidataを取得すると結果は変わり得る。授業用CSVの再作成には原本とworkディレクトリも保持する。

## 出典と利用条件

[MovieLens 32M](https://grouplens.org/datasets/movielens/32m/)、[原本README](https://files.grouplens.org/datasets/movielens/ml-32m-README.html)、[Wikidata P495](https://www.wikidata.org/wiki/Property:P495)、[P345](https://www.wikidata.org/wiki/Property:P345)。
MovieLens同梱READMEと取得時の公式HTML READMEをlicenses/に保存。双方の主要な利用条件を照合し、矛盾なし。研究利用・同条件での加工再配布が認められる。商用・収益用途は事前許可が必要。利用成果では原本の引用情報に従い、提供者の推奨・保証を示唆しない。詳細は保存した全文を参照する。
Wikidataの構造化メタデータはCC0だが、評価データを含む成果物全体はCC0ではない。**独自PythonコードのMITライセンスは、CSV・データ・統計・レポートには適用されない。** 詳細な適用範囲はリポジトリの[LICENSE.md](../../LICENSE.md)を参照する。公開・再配布時もMovieLensの同じ条件と出典を維持する。

## 期間と限界

原本の評価日時は1995-01-09T11:46:44Z〜2023-10-13T02:29:07Z。READMEの収録終期表記は2023年10月12日だが、UNIX秒から変換したUTC実測終端は13日。収録終期表記のタイムゾーンは確認できないため、差を記録し、原本timestampのUTC変換値を正として日付での切り捨ては行わない。作品年はMovieLens末尾年であり、日本公開年ではない。評価日時は鑑賞日時とは限らない。日本人や日本在住者の標本ではない。国・外部ID欠損による取りこぼしと、対象を5作品以上評価するユーザーへの選択がある。未評価を0点・嫌い・負例とみなさない。2023年作品は観測期間が短い。

予測実験はユーザー内の時系列分割を検討し、平均・標準化・特徴量を学習データだけで算出する。movies.csv/users.csvの全期間集計列を予測特徴量へそのまま使わない。5作品条件も全期間で選んだ集団内での評価である。詳細な件数、欠損、分析適性と検証結果はreport.md、型はdata_dictionary.mdを参照。
