# MovieLens 32M Japan 2020+ subset

MovieLens作品年2020年以降・日本製作国を含む作品の、小規模な評価履歴データセットです。
固定版MovieLens 32Mと、2026年10月2日に取得したWikidataの構造化データから作成しました。

## 抽出条件と結果

- MovieLensの題名末尾の作品年が2020年以上。
- IMDb IDの完全一致で一意に対応するWikidata項目のP495に日本（Q17）を含む。
- 合作・アニメ・短編を含む。作品側の最低評価数や年上限は追加しない。
- 対象作品のうち異なる5作品以上を評価したユーザーについて、対象内の全評価を残す。
- 元の匿名userId、movieId、rating、timestampを保持する。

| 指標 | 結果 |
| --- | ---: |
| 日本を含む確認済み対象作品 | 196 |
| 正式CSVの作品 | 159 |
| 正式CSVのユーザー | 176 |
| 正式CSVの評価 | 1,177 |
| 3つのCSVの合計サイズ | 101,261 bytes |
| 評価行列の密度 | 4.2060% |

Wikidataで日本を含む合作とされる『ブレット・トレイン』『NOPE/ノープ』等も含みます。
作品年は日本公開年ではありません。ユーザーは日本人・日本在住者の標本ではありません。
未照合・国欠損・競合は1,817作品あり、全邦画を網羅していません。
正式条件を緩めず、最低3・5・10作品の感度分析をレポートに併記しています。

## データと根拠

- [ratings.csv](outputs/movielens_jp_2020_min5/ratings.csv)
- [movies.csv](outputs/movielens_jp_2020_min5/movies.csv)
- [users.csv](outputs/movielens_jp_2020_min5/users.csv)
- [集計・欠損率・検証レポート](outputs/movielens_jp_2020_min5/report.md)
- [データ辞書](outputs/movielens_jp_2020_min5/data_dictionary.md)
- [manifest](outputs/movielens_jp_2020_min5/manifest.json) / [配布ファイルのSHA-256](outputs/movielens_jp_2020_min5/checksums.sha256)
- [Wikidata固定キャッシュ](work/movielens32m/metadata_cache/) / [候補・照合・検証の監査表](work/movielens32m/logs/)
- [当初の抽出仕様](movielens_32m_subset_handoff.md)

実データ検証19項目と回帰テスト8件を実施しています。原本との評価行の一致、
5作品条件、参照整合性、UTC変換、固定キャッシュからの主要CSV再生成を確認しています。

## 再現方法

Python 3.13.7で検証済み。外部Pythonパッケージは不要です。

```sh
git clone https://github.com/kofujimura/movielens-32m-japan-2020-subset.git
cd movielens-32m-japan-2020-subset

# Gitには含めない公式原本を取得し、公式チェックサムを検証する。
python3 work/movielens32m/scripts/pipeline.py download

# 同梱のWikidataキャッシュを固定して全工程を再実行する。
python3 work/movielens32m/scripts/pipeline.py all --offline --audit-ambiguities

# 回帰テスト
python3 -m unittest discover -s work/movielens32m/scripts -p 'test_*.py' -v
```

初回の原本取得にはネットワーク接続と約1.1 GBの保存領域が必要です。
`raw/`、ローカルコマンド履歴、抽出途中の評価表はGitに含めていません。
manifestには、公開していない原本の検証用ハッシュも記録しています。
主要CSVは固定キャッシュでバイト単位で再現します。実行日時を含むレポートやmanifestは更新されます。
HTTP取得記録には再現に必要な日時・URL・ハッシュ等を保持し、CookieやクライアントIPを含めません。

## ライセンスと出典

**コードのMITライセンスはデータには適用されません。リポジトリ全体をMITやCC0として扱わないでください。**

- **MovieLens由来のデータ・統計**：原本と同じ[MovieLens利用条件](outputs/movielens_jp_2020_min5/licenses/MovieLens-README.txt)を維持します。研究利用・同条件での加工再配布が認められ、商用・収益目的での利用には事前許可が必要です。
- **Wikidataの構造化データ**：CC0。結合CSV全体をCC0へ変更するものではありません。
- **独自のPythonコード**：コード部分に限り[MIT License](LICENSE-CODE)。適用範囲は[LICENSE.md](LICENSE.md)を参照してください。

このリポジトリは独立した加工成果物であり、University of Minnesota、GroupLens、Wikidataによる推奨・保証を示すものではありません。利用・再配布時は原本の条件と免責事項を維持してください。

出典：[MovieLens 32M](https://grouplens.org/datasets/movielens/32m/)、[Wikidata](https://www.wikidata.org/)、[Wikidataのライセンス](https://www.wikidata.org/wiki/Wikidata:Licensing)。

MovieLensを利用した成果物では、次の論文を引用してください。

F. Maxwell Harper and Joseph A. Konstan. 2015. *The MovieLens Datasets: History and Context*.
ACM Transactions on Interactive Intelligent Systems (TiiS) 5, 4, Article 19.
https://doi.org/10.1145/2827872

## 分析上の注意

小規模な探索・授業用データです。未評価を0点や負例とみなさないでください。
1件しか評価のない作品は標本標準偏差を空欄としています。
予測実験ではユーザー内の時系列分割を検討し、集計・標準化を学習データだけで計算してください。
付属のユーザー・作品別集計列は全期間の集計なので、そのまま予測特徴量にすると情報漏洩になります。
