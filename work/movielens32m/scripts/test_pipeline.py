# SPDX-License-Identifier: MIT
"""Regression tests for selection semantics and metadata failure handling."""
import collections
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline as p


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = []
        for name in ['RAW', 'LOG', 'CACHE', 'OUT', 'WORK']:
            directory = self.root / name
            directory.mkdir()
            q = patch.object(p, name, directory)
            q.start()
            self.patches.append(q)

    def tearDown(self):
        for q in reversed(self.patches):
            q.stop()
        self.temp.cleanup()

    def test_suffix_year_and_imdb_zero_padding(self):
        movies = [{'movieId': str(i), 'title': title, 'genres': 'Drama'} for i, title in enumerate([
            'Old (2019)', 'Recent (2020)', 'Long ID (2023) ', '2021 Inside (2020) extra', 'No Year'], 1)]
        links = [{'movieId': str(i), 'imdbId': imdb, 'tmdbId': ''} for i, imdb in enumerate(['123', '234', '12345678', '456', '567'], 1)]
        p.write_csv(p.RAW / 'ml-32m/movies.csv', ['movieId', 'title', 'genres'], movies)
        p.write_csv(p.RAW / 'ml-32m/links.csv', ['movieId', 'imdbId', 'tmdbId'], links)
        with patch.dict(p.CFG, expected_movies=5):
            result = p.candidates()
        self.assertEqual([r['imdb_id'] for r in result], ['tt0000234', 'tt12345678'])
        self.assertEqual(len(p.read_csv(p.LOG / 'year_missing.csv')), 2)

    @staticmethod
    def movie(i):
        result = {key: '' for key in p.MFIELDS}
        result.update(movieId=str(i), title=f'Film {i} (2020)', movie_year='2020', genres='Drama',
                      imdb_id=f'tt{i:07}', wikidata_qid=f'Q{i+100}', country_qids='Q17',
                      is_coproduction='false', metadata_status='jp_confirmed',
                      metadata_retrieved_at_utc='2026-01-01T00:00:00Z')
        return result

    def test_keeps_all_eligible_history_and_sample_std_missing(self):
        target_map = {i: self.movie(i) for i in range(1, 8)}
        rows = [{'userId': str(u), 'movieId': str(m), 'rating': '4.0', 'timestamp': str(1700000000 - m)}
                for u, mids in [(1, range(1, 5)), (2, range(1, 7)), (3, range(1, 6))] for m in mids]
        p.write_csv(p.LOG / 'target_ratings.csv', p.RFIELDS[:4], rows)
        with patch.object(p, 'target_movies', return_value=target_map):
            ratings, movies, users = p.make_outputs(p.OUT)
        self.assertEqual([u['userId'] for u in users], [2, 3])
        self.assertEqual(len(ratings), 11)
        self.assertEqual([m['movieId'] for m in movies], ['1', '2', '3', '4', '5', '6'])
        self.assertEqual(movies[-1]['std_rating_subset'], '')
        self.assertEqual(ratings[0]['movieId'], '6')
        self.assertEqual(p.read_csv(p.LOG / 'target_movies_without_final_ratings.csv')[0]['movieId'], '7')

    def test_distinct_movies_not_rating_rows(self):
        rows = [{'userId': '1', 'movieId': str(m), 'rating': '4.0', 'timestamp': '1'} for m in [1, 1, 2, 3, 4]]
        p.write_csv(p.LOG / 'target_ratings.csv', p.RFIELDS[:4], rows)
        with patch.object(p, 'target_movies', return_value={i: self.movie(i) for i in range(1, 5)}):
            ratings, movies, users = p.make_outputs(p.OUT)
        self.assertEqual((ratings, movies, users), ([], [], []))
        self.assertEqual((p.OUT / 'ratings.csv').read_text(), ','.join(p.RFIELDS) + '\n')

    def test_metadata_country_sets_conflicts_missing_and_non_japan(self):
        movies = [self.movie(i) for i in range(1, 7)]
        bindings = []
        for imdb, item, countries in [(1, 101, ['Q17', 'Q30']), (2, 102, ['Q30']),
                                      (3, 103, []), (5, 105, ['Q17']), (5, 106, ['Q17'])]:
            for country in countries or [None]:
                b = {'imdbId': {'value': f'tt{imdb:07}'}, 'item': {'value': f'http://www.wikidata.org/entity/Q{item}'}}
                if country:
                    b['country'] = {'value': 'http://www.wikidata.org/entity/' + country}
                bindings.append(b)

        def fake_fetch(url, path, accept):
            p.save_json(path, {'results': {'bindings': bindings}})
            return {'retrieved_at_utc': '2026-01-01T00:00:00Z'}

        with patch.object(p, 'candidates', return_value=movies), patch.object(p, 'fetch', side_effect=fake_fetch), patch.object(p.time, 'sleep'):
            p.metadata()
        rows = p.read_csv(p.LOG / 'metadata_all_candidates.csv')
        self.assertEqual([r['metadata_status'] for r in rows], ['jp_confirmed', 'other_country', 'country_missing', 'unmatched', 'ambiguous', 'unmatched'])
        self.assertEqual(rows[0]['country_qids'], 'Q17|Q30')
        self.assertEqual(rows[0]['is_coproduction'], 'true')
        self.assertEqual(len(rows), 6)

    def test_failed_fetch_is_not_unmatched_and_stops_extraction(self):
        with patch.object(p, 'candidates', return_value=[self.movie(1)]), patch.object(p, 'fetch', side_effect=OSError('network unavailable')), patch.object(p.time, 'sleep'):
            with self.assertRaisesRegex(ValueError, 'fetch_failed'):
                p.metadata()
        self.assertEqual(p.read_csv(p.LOG / 'metadata_all_candidates.csv')[0]['metadata_status'], 'fetch_failed')
        with self.assertRaisesRegex(ValueError, 'Unfinished metadata'):
            p.target_movies()

    def test_offline_never_requests_missing_response(self):
        with patch.object(p, 'candidates', return_value=[self.movie(1)]), patch.object(p, 'fetch') as fetch:
            with self.assertRaisesRegex(ValueError, 'fetch_failed'):
                p.metadata(offline=True)
            fetch.assert_not_called()

    def test_original_duplicates_are_rejected(self):
        p.write_csv(p.LOG / 'metadata_all_candidates.csv', p.MFIELDS, [self.movie(1)])
        p.write_csv(p.RAW / 'ml-32m/movies.csv', ['movieId', 'title', 'genres'], [{'movieId': '1', 'title': 'Film (2020)', 'genres': 'Drama'}])
        row = {'userId': '1', 'movieId': '1', 'rating': '4.0', 'timestamp': '1'}
        p.write_csv(p.RAW / 'ml-32m/ratings.csv', p.RFIELDS[:4], [row, row])
        with patch.object(p, 'target_movies', return_value={1: self.movie(1)}):
            with self.assertRaisesRegex(ValueError, 'Duplicate or unsorted source'):
                p.build_target_ratings()
        self.assertFalse((p.LOG / 'source_scan.json').exists())

    def test_modified_cache_is_rejected(self):
        path = p.CACHE / 'response.json'
        path.write_text('{}')
        p.save_json(path.with_suffix('.json.http.json'), {'success': True, 'status': 200, 'url': 'https://example.com', 'sha256': 'wrong'})
        with self.assertRaisesRegex(ValueError, 'Cache mismatch'):
            p.fetch('https://example.com', path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
