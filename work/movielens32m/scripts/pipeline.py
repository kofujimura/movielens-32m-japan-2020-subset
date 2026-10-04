#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproducible MovieLens 32M / Wikidata subset. Standard library only."""
import argparse
import collections
import csv
import datetime as dt
import email.utils
import gzip
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import platform
import re
import shutil
import ssl
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / 'work/movielens32m'
RAW = WORK / 'raw'
CACHE = WORK / 'metadata_cache'
LOG = WORK / 'logs'
OUT = ROOT / 'outputs/movielens_jp_2020_min5'
CONFIG_PATH = WORK / 'config.json'
CFG = json.loads(CONFIG_PATH.read_text())
BASE = 'https://files.grouplens.org/datasets/movielens/'
ENDPOINT = 'https://query.wikidata.org/sparql'
PUBLIC_HTTP_HEADERS = {'content-type', 'content-length', 'content-encoding', 'date',
                       'last-modified', 'etag', 'cache-control', 'retry-after'}
MFIELDS = ['movieId', 'title', 'title_ja', 'movie_year', 'genres', 'imdb_id',
           'wikidata_qid', 'country_qids', 'is_coproduction', 'metadata_status',
           'metadata_retrieved_at_utc']
RFIELDS = ['userId', 'movieId', 'rating', 'timestamp', 'rated_at_utc']
UFIELDS = ['userId', 'n_target_movies', 'mean_rating_subset', 'std_rating_subset',
           'first_rating_at_utc', 'last_rating_at_utc']
MOUTFIELDS = MFIELDS + ['n_ratings_subset', 'mean_rating_subset', 'std_rating_subset']


def utc(timestamp=None):
    date = dt.datetime.now(dt.timezone.utc) if timestamp is None else dt.datetime.fromtimestamp(int(timestamp), dt.timezone.utc)
    return date.isoformat(timespec='seconds').replace('+00:00', 'Z')


def digest(path, algorithm='sha256'):
    h = hashlib.new(algorithm)
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.csv.tmp')
    with open(temp, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def public_receipt(record):
    """Keep reproducibility evidence without publishing transport identifiers."""
    return {**record, 'headers': {k: v for k, v in record.get('headers', {}).items()
                                 if k.lower() in PUBLIC_HTTP_HEADERS}}


def public_audit_files():
    return [p for p in sorted(LOG.glob('*')) if p.is_file() and
            ((p.suffix in {'.json', '.csv'} and p.name != 'target_ratings.csv') or p.name == 'unit_tests.txt')]


def fetch(url, path, accept='*/*'):
    """Atomic response caching; failures never create a successful cache entry."""
    record = path.with_suffix(path.suffix + '.http.json')
    if path.exists() and record.exists():
        meta = read_json(record)
        require(meta.get('success') is True and meta.get('status') == 200 and meta['url'] == url and meta['sha256'] == digest(path), f'Cache mismatch: {path}')
        return meta
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(CFG['max_attempts']):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': CFG['user_agent'], 'Accept': accept, 'Accept-Encoding': 'gzip'})
            # python.org macOS installations may lack their own CA bundle.
            # Use the OS CA bundle, retaining TLS certificate verification.
            context = ssl.create_default_context(cafile='/etc/ssl/cert.pem') if sys.platform == 'darwin' and Path('/etc/ssl/cert.pem').exists() else ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=CFG['timeout_seconds'], context=context) as response:
                headers = {k: v for k, v in response.headers.items() if k.lower() in PUBLIC_HTTP_HEADERS}
                temp = path.with_suffix(path.suffix + '.part')
                with open(temp, 'wb') as out:
                    stream = gzip.GzipFile(fileobj=response) if response.headers.get('Content-Encoding') == 'gzip' else response
                    shutil.copyfileobj(stream, out, 1024 * 1024)
                if accept == 'application/sparql-results+json':
                    data = read_json(temp)
                    require(isinstance(data['results']['bindings'], list), 'Invalid SPARQL response')
                    require({'imdbId', 'item', 'country', 'titleJa'} <= set(data['head']['vars']), 'Incomplete SPARQL result columns')
                temp.replace(path)
                meta = {'url': url, 'retrieved_at_utc': utc(), 'success': True,
                        'status': response.status, 'headers': headers, 'sha256': digest(path), 'bytes': path.stat().st_size}
                save_json(record, meta)
                return meta
        except (OSError, ValueError, KeyError) as exc:
            delay = min(2 ** (attempt + 1), 60)
            if isinstance(exc, urllib.error.HTTPError) and exc.headers.get('Retry-After'):
                value = exc.headers['Retry-After']
                try:
                    delay = max(delay, float(value))
                except ValueError:
                    delay = max(delay, (email.utils.parsedate_to_datetime(value) - dt.datetime.now(dt.timezone.utc)).total_seconds())
            LOG.mkdir(parents=True, exist_ok=True)
            with open(LOG / 'fetch_errors.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps({'utc': utc(), 'url': url, 'attempt': attempt + 1, 'error': str(exc), 'retry_seconds': delay}) + '\n')
            print(f'fetch error {attempt + 1}: {exc}; retry in {delay}s', flush=True)
            if attempt + 1 == CFG['max_attempts']:
                raise
            time.sleep(delay)


def download(offline=False):
    def obtain(url, path):
        require(not offline or (path.exists() and path.with_suffix(path.suffix + '.http.json').exists()), f'Missing offline original: {path}')
        return fetch(url, path)

    for name in ['ml-32m.zip', 'ml-32m.zip.md5', 'ml-32m-README.html']:
        print(f'download/cache {name}', flush=True)
        obtain(BASE + name, RAW / name)
    obtain('https://grouplens.org/datasets/movielens/32m/', RAW / 'distribution-page.html')
    for name in ['Data_access', 'Licensing']:
        obtain('https://www.wikidata.org/wiki/Wikidata:' + name, RAW / ('Wikidata-' + name + '.html'))
    expected = re.search(r'\b[0-9a-fA-F]{32}\b', (RAW / 'ml-32m.zip.md5').read_text()).group().lower()
    require(digest(RAW / 'ml-32m.zip', 'md5') == expected, 'Official ZIP MD5 mismatch')
    with zipfile.ZipFile(RAW / 'ml-32m.zip') as z:
        for info in z.infolist():
            dest = (RAW / info.filename).resolve()
            require(dest.is_relative_to(RAW.resolve()), 'Unsafe ZIP path')
            require((info.external_attr >> 16) & 0o170000 != 0o120000, 'ZIP symlink forbidden')
        require(z.testzip() is None, 'ZIP CRC failure')
        for info in z.infolist():
            dest = RAW / info.filename
            if not dest.exists():
                z.extract(info, RAW)
    expected_files = {'links.csv': '8f033867bcb4e6be8792b21468b4fa6e',
                      'movies.csv': '0df90835c19151f9d819d0822e190797',
                      'ratings.csv': 'cf12b74f9ad4b94a011f079e26d4270a',
                      'tags.csv': '963bf4fa4de6b8901868fddd3eb54567'}
    html = (RAW / 'ml-32m-README.html').read_text()
    for name, md5 in expected_files.items():
        require(md5 in html, 'Official README checksum changed; investigate')
        require(digest(RAW / 'ml-32m' / name, 'md5') == md5, f'Original MD5 mismatch: {name}')
    save_json(LOG / 'download_validation.json', {'utc': utc(), 'zip_md5': expected, 'file_md5': expected_files, 'zip_crc': 'passed', 'safe_paths': 'passed'})
    print('download and official checksums verified', flush=True)


def candidates():
    movies = read_csv(RAW / 'ml-32m/movies.csv')
    links = read_csv(RAW / 'ml-32m/links.csv')
    require(len(movies) == CFG['expected_movies'], 'Unexpected MovieLens movie count')
    require(set(movies[0]) == {'movieId', 'title', 'genres'}, 'movies schema')
    require(set(links[0]) == {'movieId', 'imdbId', 'tmdbId'}, 'links schema')
    require(len({m['movieId'] for m in movies}) == len(movies), 'Duplicate movieId')
    require(len({m['movieId'] for m in links}) == len(links), 'Duplicate links movieId')
    require({m['movieId'] for m in movies} == {m['movieId'] for m in links}, 'links reference mismatch')
    linkmap = {m['movieId']: m for m in links}
    result, missing = [], []
    for m in movies:
        require(int(m['movieId']) > 0, 'Invalid movieId')
        match = re.search(r'\((\d{4})\)\s*$', m['title'])
        if not match:
            missing.append(m)
            continue
        year = int(match.group(1))
        if year < CFG['min_movie_year']:
            continue
        imdb = linkmap[m['movieId']]['imdbId']
        require(not imdb or imdb.isdigit(), 'Invalid IMDb numeric ID')
        result.append({**m, 'movie_year': year, 'imdb_id': 'tt' + imdb.zfill(7) if imdb else ''})
    result.sort(key=lambda m: int(m['movieId']))
    write_csv(LOG / 'year_missing.csv', ['movieId', 'title', 'genres'], missing)
    save_json(LOG / 'candidates_summary.json', {'movies_total': len(movies), 'year_missing': len(missing), 'candidates': len(result), 'candidate_missing_imdb': sum(not m['imdb_id'] for m in result)})
    return result


def make_query(ids):
    return '''PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?imdbId ?item ?country ?titleJa WHERE {
  VALUES ?imdbId { %s }
  ?item wdt:P345 ?imdbId .
  OPTIONAL { ?item wdt:P495 ?country . }
  OPTIONAL { ?item rdfs:label ?titleJa . FILTER(LANG(?titleJa) = "ja") }
}
''' % ' '.join(json.dumps(i) for i in ids)


def configure(min_year):
    """Keep the published 2020 profile separate from the requested 2015 profile."""
    global CFG, CONFIG_PATH, LOG, OUT
    require(min_year in (2015, 2020), 'Supported profiles: 2015 and 2020')
    CONFIG_PATH = WORK / ('config.json' if min_year == 2020 else f'config_{min_year}.json')
    CFG = read_json(CONFIG_PATH)
    require(CFG['min_movie_year'] == min_year, 'Configuration year mismatch')
    LOG = WORK / ('logs' if min_year == 2020 else f'logs_{min_year}')
    OUT = ROOT / f'outputs/movielens_jp_{min_year}_min5'


def metadata_batches(ids):
    # Preserve the original profile's exact batch keys and retrieval timestamps.
    if CFG['min_movie_year'] == 2020:
        return [ids[i:i + CFG['batch_size']] for i in range(0, len(ids), CFG['batch_size'])]
    plan_path = LOG / 'metadata_plan.json'
    signature = hashlib.sha256('\n'.join(ids).encode()).hexdigest()
    if plan_path.exists():
        plan = read_json(plan_path)
        require(plan['candidate_ids_sha256'] == signature, 'Metadata plan candidate mismatch')
        batches = plan['batches']
    else:
        remaining, batches = set(ids), []
        # Reuse complete, verified historical batches, including successful no-match results.
        # New requests cover only IDs not queried in the existing frozen snapshot.
        for path in sorted(CACHE.glob('*.rq')):
            query = path.read_text(encoding='utf-8')
            batch = re.findall(r'"(tt\d+)"', query)
            response = path.with_suffix('.json')
            receipt = response.with_suffix('.json.http.json')
            if not batch or not set(batch) <= remaining or not response.exists() or not receipt.exists():
                continue
            require(query == make_query(batch) and hashlib.sha256(query.encode()).hexdigest() == path.stem, 'Cached query integrity failure')
            meta = read_json(receipt)
            require(meta.get('success') is True and meta.get('status') == 200 and meta['sha256'] == digest(response), 'Cached response integrity failure')
            batches.append(batch)
            remaining.difference_update(batch)
        reused = sum(map(len, batches))
        pending = sorted(remaining)
        batches.extend(pending[i:i + CFG['batch_size']] for i in range(0, len(pending), CFG['batch_size']))
        save_json(plan_path, {'min_movie_year': CFG['min_movie_year'], 'candidate_ids_sha256': signature,
                             'historical_ids_reused': reused, 'new_ids': len(pending), 'batches': batches})
    flattened = [imdb for batch in batches for imdb in batch]
    require(len(flattened) == len(set(flattened)) and set(flattened) == set(ids), 'Metadata plan does not cover each candidate exactly once')
    return batches


def metadata(offline=False):
    movies = candidates()
    ids = sorted({m['imdb_id'] for m in movies if m['imdb_id']})
    by_id, failed, retrieved, evidence = collections.defaultdict(list), set(), {}, {}
    CACHE.mkdir(parents=True, exist_ok=True)
    completed = 0
    for batch in metadata_batches(ids):
        query = make_query(batch)
        key = hashlib.sha256(query.encode()).hexdigest()
        query_path, response_path = CACHE / (key + '.rq'), CACHE / (key + '.json')
        query_path.write_text(query, encoding='utf-8')
        url = ENDPOINT + '?' + urllib.parse.urlencode({'query': query, 'format': 'json'})
        cached = response_path.exists() and response_path.with_suffix('.json.http.json').exists()
        try:
            require(not offline or cached, f'Missing offline cache: {key}')
            meta = fetch(url, response_path, 'application/sparql-results+json')
            for b in read_json(response_path)['results']['bindings']:
                require(b['imdbId']['value'] in batch, 'Unexpected IMDb in response')
                by_id[b['imdbId']['value']].append(b)
            for imdb in batch:
                retrieved[imdb] = meta['retrieved_at_utc']
                evidence[imdb] = key
        except (OSError, ValueError, KeyError) as exc:
            failed.update(batch)
            print(f'batch failed {completed}: {exc}', flush=True)
        completed += len(batch)
        print(f'metadata {completed}/{len(ids)} cached={cached}', flush=True)
        if not cached and not offline:
            time.sleep(CFG['request_pause_seconds'])
    rows = []
    for m in movies:
        imdb = m['imdb_id']
        matches = by_id[imdb]
        qids = sorted({b['item']['value'].rsplit('/', 1)[-1] for b in matches})
        # Unknown-value blank nodes are not a confirmed country.
        countries = sorted({b['country']['value'].rsplit('/', 1)[-1] for b in matches
                            if 'country' in b and re.fullmatch(r'https?://www\.wikidata\.org/entity/Q\d+', b['country']['value'])})
        titles = sorted({b['titleJa']['value'] for b in matches if 'titleJa' in b})
        if imdb in failed:
            status = 'fetch_failed'
        elif not qids:
            status = 'unmatched'
        elif len(qids) != 1 or len(titles) > 1:
            status = 'ambiguous'
        elif not countries:
            status = 'country_missing'
        else:
            status = 'jp_confirmed' if CFG['country_qid'] in countries else 'other_country'
        rows.append({**m, 'title_ja': titles[0] if len(titles) == 1 and len(qids) == 1 else '',
                     'wikidata_qid': '|'.join(qids), 'country_qids': '|'.join(countries),
                     'is_coproduction': str(len(countries) > 1).lower() if countries and len(qids) == 1 else '',
                     'metadata_status': status, 'metadata_retrieved_at_utc': retrieved.get(imdb, ''),
                     'evidence_query_sha256': evidence.get(imdb, '')})
    write_csv(LOG / 'metadata_all_candidates.csv', MFIELDS + ['evidence_query_sha256'], rows)
    write_csv(LOG / 'metadata_unresolved.csv', MFIELDS + ['evidence_query_sha256'], [m for m in rows if m['metadata_status'] not in ('jp_confirmed', 'other_country')])
    save_json(LOG / 'metadata_summary.json', dict(collections.Counter(m['metadata_status'] for m in rows)))
    require(not failed, f'{len(failed)} IMDb IDs fetch_failed; resume metadata before extraction')
    print(read_json(LOG / 'metadata_summary.json'), flush=True)


def target_movies():
    require(not (WORK / 'metadata_overrides.csv').exists(), 'Manual overrides require explicit implementation/review; refusing to silently ignore a supplied file')
    rows = read_csv(LOG / 'metadata_all_candidates.csv')
    require(not any(m['metadata_status'] == 'fetch_failed' for m in rows), 'Unfinished metadata')
    require(len(rows) == read_json(LOG / 'candidates_summary.json')['candidates'], 'Incomplete candidate table')
    return {int(m['movieId']): {k: m[k] for k in MFIELDS} for m in rows if m['metadata_status'] == 'jp_confirmed'}


def audit_ambiguities(offline=False):
    """Inspect competing entities without altering the strict matching decision."""
    entries = []
    for row in read_csv(LOG / 'metadata_all_candidates.csv'):
        if row['metadata_status'] != 'ambiguous':
            continue
        for qid in row['wikidata_qid'].split('|'):
            path = CACHE / 'entity_audit' / (qid + '.json')
            require(not offline or path.exists(), 'Missing offline entity audit')
            meta = fetch(f'https://www.wikidata.org/wiki/Special:EntityData/{qid}.json', path)
            entities = read_json(path)['entities']
            entity = entities.get(qid) or next(iter(entities.values()))

            def claims(prop):
                return [{'rank': c['rank'], 'value': c['mainsnak'].get('datavalue', {}).get('value'),
                         'snaktype': c['mainsnak']['snaktype']} for c in entity.get('claims', {}).get(prop, [])]

            entries.append({'movieId': row['movieId'], 'title': row['title'], 'imdb_id': row['imdb_id'],
                            'requested_qid': qid, 'resolved_qid': entity['id'], 'lastrevid': entity.get('lastrevid'),
                            'labels': {lang: entity.get('labels', {}).get(lang, {}).get('value') for lang in ['ja', 'en']},
                            'descriptions': {lang: entity.get('descriptions', {}).get(lang, {}).get('value') for lang in ['ja', 'en']},
                            'P31': claims('P31'), 'P345': claims('P345'), 'P495': claims('P495'),
                            'retrieved_at_utc': meta['retrieved_at_utc'], 'url': meta['url'],
                            'decision': 'ambiguous retained; no override'})
            if not offline:
                time.sleep(CFG['request_pause_seconds'])
    save_json(LOG / 'ambiguity_entity_audit.json', entries)
    print(f'audited {len(entries)} competing entities; formal classification unchanged', flush=True)


def build_target_ratings():
    targets = target_movies()
    candidate_meta = read_csv(LOG / 'metadata_all_candidates.csv')
    candidate_ids = {int(m['movieId']) for m in candidate_meta}
    candidate_counts = collections.Counter()
    known_movies = {int(m['movieId']) for m in read_csv(RAW / 'ml-32m/movies.csv')}
    path = LOG / 'target_ratings.csv'
    temp = path.with_suffix('.csv.tmp')
    n, previous, users, tmin, tmax = 0, (0, 0), set(), None, None
    with open(RAW / 'ml-32m/ratings.csv', newline='', encoding='utf-8') as src, open(temp, 'w', newline='', encoding='utf-8') as dest:
        reader = csv.reader(src)
        require(next(reader) == RFIELDS[:4], 'ratings schema mismatch')
        writer = csv.writer(dest, lineterminator='\n')
        writer.writerow(RFIELDS[:4])
        for row in reader:
            require(len(row) == 4, 'ratings malformed row')
            u, m, rating, timestamp = int(row[0]), int(row[1]), float(row[2]), int(row[3])
            require(u > 0 and m in known_movies, 'Invalid source ID')
            require((u, m) > previous, 'Duplicate or unsorted source userId/movieId; investigate, never deduplicate')
            require(0.5 <= rating <= 5.0 and rating * 2 == int(rating * 2), 'Invalid source rating')
            previous = (u, m)
            users.add(u)
            tmin = min(tmin, timestamp) if tmin is not None else timestamp
            tmax = max(tmax, timestamp) if tmax is not None else timestamp
            n += 1
            if m in candidate_ids:
                candidate_counts[m] += 1
            if m in targets:
                writer.writerow(row)
            if n % 4000000 == 0:
                print(f'source scan {n:,}', flush=True)
    require(n == CFG['expected_ratings'], 'Source rating count mismatch')
    require(len(users) == CFG['expected_users'], 'Source user count mismatch')
    temp.replace(path)
    write_csv(LOG / 'candidate_rating_coverage.csv', MFIELDS + ['evidence_query_sha256', 'n_ratings_original'],
              [{**m, 'n_ratings_original': candidate_counts[int(m['movieId'])]} for m in candidate_meta])
    save_json(LOG / 'source_scan.json', {'utc': utc(), 'ratings': n, 'users': len(users),
              'timestamp_min': tmin, 'timestamp_max': tmax, 'rated_at_utc_min': utc(tmin), 'rated_at_utc_max': utc(tmax),
              'ratings_sha256': digest(RAW / 'ml-32m/ratings.csv'), 'target_ratings_sha256': digest(path),
              'metadata_sha256': digest(LOG / 'metadata_all_candidates.csv'),
              'checks': ['all_source_ids_valid', 'all_source_ratings_valid', 'all_source_pairs_unique_and_sorted']})


def stat(values):
    return {'min': min(values), 'median': statistics.median(values), 'max': max(values)} if values else {'min': None, 'median': None, 'max': None}


def aggregate(values):
    return {'mean_rating_subset': statistics.mean(values),
            'std_rating_subset': statistics.stdev(values) if len(values) > 1 else ''}


def make_outputs(destination):
    targets = target_movies()
    target_rows = read_csv(LOG / 'target_ratings.csv')
    per_user = collections.defaultdict(set)
    for r in target_rows:
        per_user[int(r['userId'])].add(int(r['movieId']))
    eligible = {u for u, mids in per_user.items() if len(mids) >= CFG['min_target_movies_per_user']}
    final = [r for r in target_rows if int(r['userId']) in eligible]
    final.sort(key=lambda r: (int(r['userId']), int(r['timestamp']), int(r['movieId'])))
    user_rows, movie_rows = collections.defaultdict(list), collections.defaultdict(list)
    for r in final:
        r['rated_at_utc'] = utc(r['timestamp'])
        user_rows[int(r['userId'])].append(r)
        movie_rows[int(r['movieId'])].append(r)
    users = [{'userId': u, 'n_target_movies': len({r['movieId'] for r in rows}),
              **aggregate([float(r['rating']) for r in rows]),
              'first_rating_at_utc': min(r['rated_at_utc'] for r in rows),
              'last_rating_at_utc': max(r['rated_at_utc'] for r in rows)} for u, rows in sorted(user_rows.items())]
    movies = [{**targets[m], 'n_ratings_subset': len(rows), **aggregate([float(r['rating']) for r in rows])}
              for m, rows in sorted(movie_rows.items())]
    write_csv(destination / 'ratings.csv', RFIELDS, final)
    write_csv(destination / 'movies.csv', MOUTFIELDS, movies)
    write_csv(destination / 'users.csv', UFIELDS, users)
    if destination == OUT:
        write_csv(LOG / 'target_movies_without_final_ratings.csv', MFIELDS, [v for k, v in sorted(targets.items()) if k not in movie_rows])
        sensitivity = []
        for threshold in [3, 5, 10]:
            us = {u for u, mids in per_user.items() if len(mids) >= threshold}
            rs = [r for r in target_rows if int(r['userId']) in us]
            sensitivity.append({'min_target_movies_per_user': threshold, 'users': len(us),
                                'movies': len({r['movieId'] for r in rs}), 'ratings': len(rs)})
        save_json(LOG / 'extract_summary.json', {'jp_confirmed': len(targets), 'target_ratings': len(target_rows),
                  'target_users': len(per_user), 'target_movies_with_ratings': len({r['movieId'] for r in target_rows}),
                  'final_movies': len(movies), 'final_users': len(users), 'final_ratings': len(final),
                  'targets_without_final_ratings': len(targets) - len(movies), 'sensitivity': sensitivity})
    return final, movies, users


def extract():
    checkpoint = LOG / 'source_scan.json'
    reusable = checkpoint.exists() and (LOG / 'target_ratings.csv').exists()
    if reusable:
        scan = read_json(checkpoint)
        reusable = (scan['metadata_sha256'] == digest(LOG / 'metadata_all_candidates.csv')
                    and scan['ratings_sha256'] == digest(RAW / 'ml-32m/ratings.csv')
                    and scan['target_ratings_sha256'] == digest(LOG / 'target_ratings.csv'))
    if not reusable:
        build_target_ratings()
    make_outputs(OUT)
    print(read_json(LOG / 'extract_summary.json'), flush=True)


def validate():
    # Persist failure by default, so an interrupted run cannot look verified.
    save_json(LOG / 'validation.json', {'passed': False, 'started_at_utc': utc()})
    checks = []

    def check(condition, name):
        require(condition, name)
        checks.append({'check': name, 'passed': True})

    ratings, movies, users = (read_csv(OUT / name) for name in ['ratings.csv', 'movies.csv', 'users.csv'])
    targets = target_movies()
    movie_map = {int(m['movieId']): m for m in movies}
    user_map = {int(u['userId']): u for u in users}
    check(len(movie_map) == len(movies) and len(user_map) == len(users), 'primary_keys_unique')
    by_user, by_movie = collections.defaultdict(list), collections.defaultdict(list)
    actual = {}
    scan = read_json(LOG / 'source_scan.json')
    for r in ratings:
        u, m, t, value = int(r['userId']), int(r['movieId']), int(r['timestamp']), float(r['rating'])
        require(u in user_map and m in movie_map and m in targets, 'references / target membership')
        require((u, m) not in actual, 'Duplicate final user/movie')
        require(0.5 <= value <= 5 and value * 2 == int(value * 2), 'Rating domain')
        require(r['rated_at_utc'] == dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'UTC conversion')
        require(scan['timestamp_min'] <= t <= scan['timestamp_max'], 'Timestamp bounds')
        actual[(u, m)] = (r['rating'], r['timestamp'])
        by_user[u].append(r)
        by_movie[m].append(r)
    check(set(by_user) == set(user_map) and set(by_movie) == set(movie_map), 'reference_integrity_exact_no_unused_rows')
    check(all(len({r['movieId'] for r in rows}) >= 5 for rows in by_user.values()), 'all_users_at_least_5_distinct_target_movies')
    check(all(int(m['movie_year']) >= CFG['min_movie_year'] and 'Q17' in m['country_qids'].split('|') and m['metadata_status'] == 'jp_confirmed' for m in movies), 'year_and_country_criteria')
    for m in movies:
        require(all(m[k] == targets[int(m['movieId'])][k] for k in MFIELDS), 'Metadata not equal to evidence table')
    checks.extend({'check': c, 'passed': True} for c in ['rating_domain', 'final_user_movie_unique', 'utc_conversion_and_source_bounds', 'metadata_matches_evidence'])
    check(sum(int(u['n_target_movies']) for u in users) == len(ratings), 'user_count_sum')
    check(sum(int(m['n_ratings_subset']) for m in movies) == len(ratings), 'movie_count_sum')
    for table, grouped, idfield, countfield in [(users, by_user, 'userId', 'n_target_movies'), (movies, by_movie, 'movieId', 'n_ratings_subset')]:
        for entry in table:
            rows = grouped[int(entry[idfield])]
            values = [float(r['rating']) for r in rows]
            require(int(entry[countfield]) == len(rows), 'Group count mismatch')
            require(abs(float(entry['mean_rating_subset']) - sum(values) / len(values)) < 1e-12, 'Mean mismatch')
            if len(values) == 1:
                require(entry['std_rating_subset'] == '', 'Singleton sample std must be missing')
            else:
                mean = sum(values) / len(values)
                independent_std = (sum((x - mean) ** 2 for x in values) / (len(values) - 1)) ** .5
                require(abs(float(entry['std_rating_subset']) - independent_std) < 1e-12, 'Sample std mismatch')
            if idfield == 'userId':
                require(entry['first_rating_at_utc'] == min(r['rated_at_utc'] for r in rows) and entry['last_rating_at_utc'] == max(r['rated_at_utc'] for r in rows), 'User date aggregate mismatch')
    checks.append({'check': 'all_aggregates_independently_recomputed_ddof1', 'passed': True})
    check(ratings == sorted(ratings, key=lambda r: (int(r['userId']), int(r['timestamp']), int(r['movieId']))), 'stable_sort_order')
    # Independent raw-file pass verifies both row equality and omission-free eligibility.
    expected, target_users, source_n = {}, collections.defaultdict(set), 0
    with open(RAW / 'ml-32m/ratings.csv', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            source_n += 1
            m = int(row[1])
            if m in targets:
                u = int(row[0])
                target_users[u].add(m)
                if u in user_map:
                    require((u, m) not in expected, 'Duplicate raw row')
                    expected[(u, m)] = (row[2], row[3])
            if source_n % 8000000 == 0:
                print(f'independent validation {source_n:,}', flush=True)
    check(source_n == CFG['expected_ratings'], 'independent_source_count')
    check({u for u, mids in target_users.items() if len(mids) >= 5} == set(user_map), 'eligible_user_set_exact_from_original')
    check(actual == expected, 'every_final_rating_exact_original_and_all_eligible_rows_retained')
    if CFG['min_movie_year'] == 2015:
        baseline = ROOT / 'outputs/movielens_jp_2020_min5/ratings.csv'
        if baseline.exists():
            previous = {(int(r['userId']), int(r['movieId'])): (r['rating'], r['timestamp']) for r in read_csv(baseline)}
            check(all(actual.get(k) == v for k, v in previous.items()), 'all_2020_final_ratings_preserved_in_2015')
        baseline_meta = WORK / 'logs/metadata_all_candidates.csv'
        if baseline_meta.exists():
            current = {m['movieId']: m for m in read_csv(LOG / 'metadata_all_candidates.csv')}
            check(all(current.get(m['movieId']) == m for m in read_csv(baseline_meta)), 'all_2020_metadata_and_retrieval_timestamps_preserved')
    before_metadata = digest(LOG / 'metadata_all_candidates.csv')
    metadata(offline=True)
    check(digest(LOG / 'metadata_all_candidates.csv') == before_metadata, 'frozen_response_cache_rebuilds_identical_metadata')
    replay = LOG / 'reproducibility'
    make_outputs(replay)
    for name in ['ratings.csv', 'movies.csv', 'users.csv']:
        check(digest(OUT / name) == digest(replay / name), 'frozen_cache_replay_sha256_' + name)
    hashes = {name: digest(OUT / name) for name in ['ratings.csv', 'movies.csv', 'users.csv']}
    save_json(LOG / 'validation.json', {'passed': True, 'completed_at_utc': utc(), 'checks': checks, 'csv_sha256': hashes})
    print(f'{len(checks)} validations passed', flush=True)


def graph_stats(ratings):
    parent = {}

    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for r in ratings:
        a, b = find('u' + r['userId']), find('m' + r['movieId'])
        parent[a] = b
    groups = collections.defaultdict(lambda: {'users': 0, 'movies': 0})
    for node in list(parent):
        groups[find(node)]['users' if node.startswith('u') else 'movies'] += 1
    largest = max(groups.values(), key=lambda v: v['users'] + v['movies'], default={'users': 0, 'movies': 0})
    return {'components': len(groups), 'largest': largest}


def markdown_table(headers, rows):
    def cell(v):
        return str(v).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |'] + ['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows])


def overlap_stats(ratings):
    users = collections.defaultdict(set)
    movies = set()
    for row in ratings:
        users[row['userId']].add(int(row['movieId']))
        movies.add(row['movieId'])
    shared = collections.Counter()
    for movie_ids in users.values():
        shared.update(itertools.combinations(sorted(movie_ids), 2))
    total = len(movies) * (len(movies) - 1) // 2
    return {'total_pairs': total, 'zero_overlap': total - len(shared),
            'at_least': {str(k): sum(n >= k for n in shared.values()) for k in [1, 2, 3, 5, 10, 20]}}


def compare_with_2020(summary, ratings, movies, users):
    previous_dir = ROOT / 'outputs/movielens_jp_2020_min5'
    if CFG['min_movie_year'] != 2015 or not (previous_dir / 'ratings.csv').exists():
        return
    old_ratings, old_movies, old_users = (read_csv(previous_dir / name) for name in ['ratings.csv', 'movies.csv', 'users.csv'])
    old_overlap = overlap_stats(old_ratings)
    old_density = len(old_ratings) / (len(old_users) * len(old_movies)) if old_users and old_movies else None
    comparison = {
        '2020': {'movies': len(old_movies), 'users': len(old_users), 'ratings': len(old_ratings),
                 'csv_bytes': sum((previous_dir / name).stat().st_size for name in ['ratings.csv', 'movies.csv', 'users.csv']),
                 'density': old_density, 'item_pair_overlap': old_overlap},
        '2015': {'movies': len(movies), 'users': len(users), 'ratings': len(ratings),
                 'csv_bytes': summary['csv_total_bytes'], 'density': summary['density'],
                 'item_pair_overlap': summary['item_pair_overlap']}}
    save_json(LOG / 'edition_comparison.json', comparison)
    count_rows = [[label, comparison['2020'][key], comparison['2015'][key],
                   f"{comparison['2015'][key] / comparison['2020'][key]:.2f}倍" if comparison['2020'][key] else '計算不能']
                  for label, key in [('作品数', 'movies'), ('ユーザー数', 'users'), ('評価数', 'ratings'), ('CSV bytes', 'csv_bytes')]]
    pair_rows = [['全作品ペア', old_overlap['total_pairs'], summary['item_pair_overlap']['total_pairs']],
                 ['共通評価者0人', old_overlap['zero_overlap'], summary['item_pair_overlap']['zero_overlap']]]
    pair_rows.extend([f'共通評価者{k}人以上', old_overlap['at_least'][k], n] for k, n in summary['item_pair_overlap']['at_least'].items())
    text = '\n'.join([
        '# 2020年版と2015年版の比較', '',
        '変更した抽出条件はMovieLens作品年の下限のみ。日本Q17を含む一意照合、合作・アニメ・短編を含むこと、対象内5作品以上のユーザーの全評価を保持する条件は共通。作品年上限・作品側最低件数・間引きは追加していない。', '',
        markdown_table(['指標', '2020年以降', '2015年以降', '倍率'], count_rows), '',
        markdown_table(['指標', '2020年以降', '2015年以降'], [
            ['行列密度', f'{old_density:.4%}' if old_density is not None else '計算不能', f"{summary['density']:.4%}" if summary['density'] is not None else '計算不能']]), '',
        '## 作品類似度に利用できる観測', '',
        markdown_table(['作品ペアの共通評価者数', '2020年以降', '2015年以降'], pair_rows), '',
        '対象作品と評価者も増えるため、評価件数の増加が密度の上昇を意味するとは限らない。共通評価者が少ないペアは依然として不安定であり、未評価を0点で埋める根拠にはならない。', '',
        '## 比較の再現性', '',
        '2020年以降の7,986候補は既存のWikidata応答を再利用し、取得時刻も維持した。2015〜2019年の15,780候補のみ追加取得した。メタデータの取得時点は混在するが、既存対象の再取得による変化はない。元の2020年版の全評価が2015年版にも同値で含まれることを検証している。', '',
        '既存版の作品・ユーザーごとの平均値を新しい評価表へ流用せず、集計列はそれぞれの抽出内で計算している。', '',
        '再実行: `python3 work/movielens32m/scripts/pipeline.py all --min-year 2015 --offline`。元の2020年版は同じoutputs配下に保持する。', ''])
    (OUT / 'comparison_2020.md').write_text(text, encoding='utf-8')


def report():
    year = CFG['min_movie_year']
    year_option = f' --min-year {year}'
    log_name = LOG.name
    validation = read_json(LOG / 'validation.json')
    require(validation['passed'], 'Cannot publish a verified report after validation failure')
    for name, sha in validation['csv_sha256'].items():
        require(digest(OUT / name) == sha, 'CSV changed after validation')
    ratings, movies, users = (read_csv(OUT / name) for name in ['ratings.csv', 'movies.csv', 'users.csv'])
    allmeta = read_csv(LOG / 'metadata_all_candidates.csv')
    cs, es, scan = (read_json(LOG / n) for n in ['candidates_summary.json', 'extract_summary.json', 'source_scan.json'])
    states = collections.Counter(m['metadata_status'] for m in allmeta)
    filesizes = {n: (OUT / n).stat().st_size for n in ['ratings.csv', 'movies.csv', 'users.csv']}
    missing = {name: {k: {'missing': sum(r[k] == '' for r in rows), 'total': len(rows),
                        'rate': sum(r[k] == '' for r in rows) / len(rows) if rows else None} for k in fields}
               for name, rows, fields in [('ratings.csv', ratings, RFIELDS), ('movies.csv', movies, MOUTFIELDS), ('users.csv', users, UFIELDS)]}
    graph = graph_stats(ratings)
    audit_path = LOG / 'ambiguity_entity_audit.json'
    audit_entries = read_json(audit_path) if audit_path.exists() else []
    audit_section = ('競合項目の追加EntityData監査は未実施。SPARQLの各対応項目と国はキャッシュに保存している。' if not audit_entries else
                     f'競合項目の追加EntityData監査は{len(audit_entries)}記録。P31・P345・P495、ラベル、説明、リビジョンを保存した。'
                     '同一IMDb IDの複数項目への対応はambiguousのまま除外し、手動補正による追加は行っていない。'
                     f'追加根拠は{log_name}/ambiguity_entity_audit.jsonおよびmetadata_cache/entity_audit/に保存。')
    density = len(ratings) / (len(users) * len(movies)) if users and movies else None
    summary = {'created_at_utc': utc(), 'candidates': cs, 'metadata_status': dict(states), 'extraction': es,
               'file_sizes_bytes': filesizes, 'csv_total_bytes': sum(filesizes.values()), 'missingness': missing,
               'density': density, 'graph': graph, 'user_rating_counts': stat([int(u['n_target_movies']) for u in users]),
               'movie_rating_counts': stat([int(m['n_ratings_subset']) for m in movies]),
               'rating_distribution': dict(sorted(collections.Counter(r['rating'] for r in ratings).items())),
               'year_counts': dict(sorted(collections.Counter(m['movie_year'] for m in movies).items())),
               'genre_counts': dict(sorted(collections.Counter(g for m in movies for g in m['genres'].split('|')).items())),
               'animation_movies': sum('Animation' in m['genres'].split('|') for m in movies),
               'coproduction_movies': sum(m['is_coproduction'] == 'true' for m in movies),
               'item_pair_overlap': overlap_stats(ratings),
               'metadata_retrieval_range_utc': [min(m['metadata_retrieved_at_utc'] for m in allmeta if m['metadata_retrieved_at_utc']),
                                                max(m['metadata_retrieved_at_utc'] for m in allmeta if m['metadata_retrieved_at_utc'])]}
    save_json(LOG / 'report_summary.json', summary)
    lic = OUT / 'licenses'
    lic.mkdir(exist_ok=True)
    shutil.copyfile(RAW / 'ml-32m/README.txt', lic / 'MovieLens-README.txt')
    shutil.copyfile(RAW / 'ml-32m-README.html', lic / 'MovieLens-current-README.html')
    bundled = (RAW / 'ml-32m/README.txt').read_text()
    online = (RAW / 'ml-32m-README.html').read_text()
    clauses = ['same license conditions', 'commercial or revenue-bearing', 'must acknowledge', 'may not state or imply']
    require(all(c in bundled and c in online for c in clauses), 'License discrepancy: manual review required')
    (lic / 'Wikidata.md').write_text('Wikidataの構造化データ（P345、P495、日本語ラベル）はCC0。\n出典: https://www.wikidata.org/wiki/Wikidata:Licensing\nCC0: https://creativecommons.org/publicdomain/zero/1.0/\nアクセス方針: https://www.wikidata.org/wiki/Wikidata:Data_access\n取得日時・照会・応答は metadata_cache/ に保存。Web解説ページの文章のライセンスと構造化データのCC0は区別する。\nMovieLens評価・題名・ジャンルおよび全成果物をCC0と表示してはいけない。\n', encoding='utf-8')
    source_line = '[MovieLens 32M](https://grouplens.org/datasets/movielens/32m/)、[原本README](https://files.grouplens.org/datasets/movielens/ml-32m-README.html)、[Wikidata P495](https://www.wikidata.org/wiki/Property:P495)、[P345](https://www.wikidata.org/wiki/Property:P345)。'
    readme = f'''# MovieLens作品年{year}年以降・日本製作国を含む作品

元データは固定版ml-32m。title末尾の4桁年が{year}以上、IMDb ID完全一致で一意に対応したWikidataのP495にQ17を含む作品を対象とする。その対象内で異なるmovieIdを5作品以上評価したユーザーの対象内評価を全件残す。合作・アニメ・短編を含む。作品側の最低評価数、年上限、ランダム間引きは設けない。元の匿名userId/movieId、rating、timestampを維持する。

正式成果物は{len(movies):,}作品・{len(users):,}ユーザー・{len(ratings):,}評価。CSV合計{sum(filesizes.values()):,} bytes。評価表はuserId、timestamp、movieIdの昇順。作品表とユーザー表は各ID昇順。UTF-8、BOMなし、LF改行。

## 再実行

コマンドはこのリポジトリのルートで実行する。Python {platform.python_version()}の標準ライブラリのみ。依存追加は不要。

```sh
python3 work/movielens32m/scripts/pipeline.py download{year_option}
python3 work/movielens32m/scripts/pipeline.py metadata{year_option}
python3 work/movielens32m/scripts/pipeline.py extract{year_option}
python3 work/movielens32m/scripts/pipeline.py validate{year_option}
python3 work/movielens32m/scripts/pipeline.py report{year_option}
```

GitHubの公開版にはraw/を含めない。初回は上記downloadで公式原本を取得する。その後、固定キャッシュで全工程を再実行: `python3 work/movielens32m/scripts/pipeline.py all --offline{year_option}`。
競合の追加監査を含める場合は `python3 work/movielens32m/scripts/pipeline.py metadata --audit-ambiguities --offline{year_option}`。キャッシュがない初回は--offlineを外す。監査は選定結果を変更しない。回帰テスト: `python3 -m unittest discover -s work/movielens32m/scripts -p 'test_*.py' -v`。
downloadの再利用時も原本チェックサムを検証する。通信失敗はfetch_failedとして記録し、metadataを再実行すれば成功済みバッチを再利用する。失敗が残れば抽出を停止する。キャッシュ取得時刻も固定するため主要CSVはバイト単位で再現する。レポート・manifestの実行時刻は更新される。

原本は `work/movielens32m/raw/`、クエリ・JSON応答・HTTP取得情報は `work/movielens32m/metadata_cache/`、候補全件・欠損年・未解決照合・最終評価が残らなかった対象作品は `work/movielens32m/{log_name}/`。候補表のevidence_query_sha256から同名の.rqと.jsonを参照できる。手動補正は行っていない。キャッシュ固定が再現の前提であり、将来新規にWikidataを取得すると結果は変わり得る。授業用CSVの再作成には原本とworkディレクトリも保持する。

2015年版は2020年版の候補照合をそのまま再利用し、追加年の候補のみ新規取得する。2015年版の照会バッチ計画はlogs_2015/metadata_plan.jsonに固定する。取得時刻の範囲は{summary['metadata_retrieval_range_utc'][0]}〜{summary['metadata_retrieval_range_utc'][1]}。既存版のCSVやメタデータは上書きしない。

## 出典と利用条件

{source_line}
MovieLens同梱READMEと取得時の公式HTML READMEをlicenses/に保存。双方の主要な利用条件を照合し、矛盾なし。研究利用・同条件での加工再配布が認められる。商用・収益用途は事前許可が必要。利用成果では原本の引用情報に従い、提供者の推奨・保証を示唆しない。詳細は保存した全文を参照する。
Wikidataの構造化メタデータはCC0だが、評価データを含む成果物全体はCC0ではない。**独自PythonコードのMITライセンスは、CSV・データ・統計・レポートには適用されない。** 詳細な適用範囲はリポジトリの[LICENSE.md](../../LICENSE.md)を参照する。公開・再配布時もMovieLensの同じ条件と出典を維持する。

## 期間と限界

原本の評価日時は{scan['rated_at_utc_min']}〜{scan['rated_at_utc_max']}。READMEの収録終期表記は2023年10月12日だが、UNIX秒から変換したUTC実測終端は13日。収録終期表記のタイムゾーンは確認できないため、差を記録し、原本timestampのUTC変換値を正として日付での切り捨ては行わない。作品年はMovieLens末尾年であり、日本公開年ではない。評価日時は鑑賞日時とは限らない。日本人や日本在住者の標本ではない。国・外部ID欠損による取りこぼしと、対象を5作品以上評価するユーザーへの選択がある。未評価を0点・嫌い・負例とみなさない。2023年作品は観測期間が短い。

予測実験はユーザー内の時系列分割を検討し、平均・標準化・特徴量を学習データだけで算出する。movies.csv/users.csvの全期間集計列を予測特徴量へそのまま使わない。5作品条件も全期間で選んだ集団内での評価である。詳細な件数、欠損、分析適性と検証結果はreport.md、型はdata_dictionary.mdを参照。
'''
    (OUT / 'README.md').write_text(readme, encoding='utf-8')
    meanings = {
        'userId': ('integer', '原本の匿名ユーザーID。全ファイル共通'), 'movieId': ('integer', '原本の作品ID。全ファイル共通'),
        'rating': ('number', '原本評価。0.5〜5.0の0.5刻み'), 'timestamp': ('integer', '原本のUNIX秒'),
        'rated_at_utc': ('string', 'timestampをISO 8601 UTCへ変換。末尾Z'),
        'title': ('string', 'MovieLens原題名（末尾年を保持）'), 'title_ja': ('string/null', 'Wikidata日本語ラベル。欠損は創作せず空欄。表示時はtitleへフォールバック'),
        'movie_year': ('integer', 'title末尾の括弧内4桁年'), 'genres': ('string', '原本ジャンル。|区切り。(no genres listed)は原本の欠損相当表記'),
        'imdb_id': ('string', 'tt + 数字最低7桁。8桁以上を切り捨てない'), 'wikidata_qid': ('string', '一意な対応作品QID'),
        'country_qids': ('string', 'P495国QID集合。重複除去・文字列昇順・|区切り'),
        'is_coproduction': ('boolean', 'true/false。取得した国集合が2か国以上ならtrue。欠損国がある可能性は残る'),
        'metadata_status': ('string', '正式作品表はjp_confirmedのみ'), 'metadata_retrieved_at_utc': ('string', '対応バッチの取得完了日時。UTC・末尾Z'),
        'n_ratings_subset': ('integer', '正式抽出内の作品別評価行数'), 'mean_rating_subset': ('number', '正式抽出内の算術平均'),
        'std_rating_subset': ('number/null', '正式抽出内の標本標準偏差ddof=1。1件は空欄'),
        'n_target_movies': ('integer', '正式抽出内の異なる対象movieId数'),
        'first_rating_at_utc': ('string', '抽出内の最初の評価日時UTC'), 'last_rating_at_utc': ('string', '抽出内の最後の評価日時UTC')}
    dictionary = '# データ辞書\n\nCSVはUTF-8、カンマ区切り、引用符はCSV標準、欠損は空欄。数値は小数点.、日時はUTC。作品ID・ユーザーIDを再採番しない。標準偏差の空欄を0に置換しない。\n'
    for name, fields in [('ratings.csv', RFIELDS), ('movies.csv', MOUTFIELDS), ('users.csv', UFIELDS)]:
        dictionary += '\n## ' + name + '\n\n' + markdown_table(['列', '型', '意味'], [[k, *meanings[k]] for k in fields]) + '\n'
    dictionary += '\n監査表metadata_all_candidates.csvは1 movieIdにつき1行。ambiguous行のQID・国集合は複数候補の監査情報であり、対象判定に利用しない。evidence_query_sha256は保存SPARQL本文のSHA-256。unmatchedは外部IDなしまたは正常応答で一致なし、country_missingは一意な照合先の国欠損、fetch_failedは取得失敗を表す。\n'
    (OUT / 'data_dictionary.md').write_text(dictionary, encoding='utf-8')
    popular = sorted(movies, key=lambda m: (-int(m['n_ratings_subset']), int(m['movieId'])))[:10]
    divided = sorted([m for m in movies if m['std_rating_subset']], key=lambda m: (-float(m['std_rating_subset']), -int(m['n_ratings_subset']), int(m['movieId'])))[:10]
    nonjp = [m for m in allmeta if m['metadata_status'] not in ('jp_confirmed', 'other_country')]
    unresolved_coverage = sorted([m for m in read_csv(LOG / 'candidate_rating_coverage.csv')
                                 if m['metadata_status'] not in ('jp_confirmed', 'other_country')],
                                key=lambda m: (-int(m['n_ratings_original']), int(m['movieId'])))
    years = [int(m['movie_year']) for m in movies]
    final_dates = [r['rated_at_utc'] for r in ratings]
    future = [m for m in allmeta if int(m['movie_year']) > int(scan['rated_at_utc_max'][:4])]
    write_csv(LOG / 'years_after_collection_end.csv', MFIELDS + ['evidence_query_sha256'], future)
    lines = ['# 抽出・検証レポート', '', f'生成日時: {utc()}。正式条件: MovieLens作品年{year}年以降・P495に日本Q17を含む一意照合作品・対象内5作品以上のユーザー。指定年以外の抽出条件は元の仕様を維持。', '',
             '## 処理段階', '', markdown_table(['段階', '件数'], [
                 ['原本作品', cs['movies_total']], ['原本評価', scan['ratings']], ['原本ユーザー', scan['users']],
                 ['作品年欠損（推測補完せず別表）', cs['year_missing']], [f'{year}年以上候補', cs['candidates']],
                 *[[status, states.get(status, 0)] for status in ['jp_confirmed', 'other_country', 'country_missing', 'unmatched', 'ambiguous', 'fetch_failed']],
                 ['対象作品への全評価', es['target_ratings']], ['対象内1件以上のユーザー', es['target_users']],
                 ['5作品条件後の作品', len(movies)], ['5作品条件後のユーザー', len(users)], ['5作品条件後の評価', len(ratings)],
                 ['対象だが正式評価が残らない作品', es['targets_without_final_ratings']]]), '',
             '## 照合と欠損', '',
             f"年欠損: {cs['year_missing']}/{cs['movies_total']} ({cs['year_missing']/cs['movies_total']:.2%})。候補のIMDb欠損: {cs['candidate_missing_imdb']}。未解決: {len(nonjp)}/{len(allmeta)} ({len(nonjp)/len(allmeta):.2%})。未解決は非邦画と同一視しない。手動補正は0件。全候補の照合と根拠キーはlogs/metadata_all_candidates.csv、未解決はlogs/metadata_unresolved.csv。", '',
             markdown_table(['状態', '候補中の件数', '候補を分母とする率'], [[s, states.get(s, 0), f'{states.get(s, 0)/len(allmeta):.2%}'] for s in ['jp_confirmed', 'other_country', 'country_missing', 'unmatched', 'ambiguous', 'fetch_failed']]), '',
             '未解決のうち原本評価件数の多い候補を以下に示す。日本作品の候補と確定した一覧ではなく、照合改善の優先確認先である。題名だけで国を推定せず正式対象へ追加していない。全候補の原本評価件数はlogs/candidate_rating_coverage.csv。', '',
             markdown_table(['movieId', '原題名', '状態', '原本評価数', '対応QID'], [[m['movieId'], m['title'], m['metadata_status'], m['n_ratings_original'], m['wikidata_qid']] for m in unresolved_coverage[:10]]), '',
             '複数項目に対応したIMDb IDは各項目の国を合算して日本と判定せず、ambiguousとして保留する。', '',
             markdown_table(['movieId', '原題名', 'IMDb ID', '競合QID'], [[m['movieId'], m['title'], m['imdb_id'], m['wikidata_qid']] for m in allmeta if m['metadata_status'] == 'ambiguous']), '',
             audit_section, '',
             markdown_table(['movieId', '項目（出典リンク）', '日本語ラベル', '項目の説明'], [[e['movieId'], f"[{e['requested_qid']}]({e['url']})", e['labels'].get('ja') or '', e['descriptions'].get('ja') or e['descriptions'].get('en') or '記載なし'] for e in audit_entries]), '',
             '正式CSVの全列について空欄率を示す。ジャンルの(no genres listed)は空欄率に含まないため別記する。', '',
             markdown_table(['CSV', '列', '欠損/行数', '欠損率'], [[name, col, f"{v['missing']}/{v['total']}", f"{v['rate']:.2%}" if v['rate'] is not None else '計算不能'] for name, cols in missing.items() for col, v in cols.items()]), '',
             f"ジャンル未登録: {sum(m['genres'] == '(no genres listed)' for m in movies)}作品。日本語タイトル欠損時も原題名titleを保持。国情報の欠落・誤りにより取りこぼしがあり、全邦画の網羅表ではない。", '',
             '## 作品構成と期間', '',
             '以下の内訳は正式CSV内の作品数。ジャンルは複数計上されるため合計は作品数を超える。', '',
             markdown_table(['作品年', '作品数'], sorted(summary['year_counts'].items())), '',
             markdown_table(['ジャンル', '作品数'], sorted(summary['genre_counts'].items())), '',
             f"Animationあり {summary['animation_movies']}作品、それ以外 {len(movies)-summary['animation_movies']}作品。日本を含む複数国 {summary['coproduction_movies']}作品、取得国集合が日本のみ {len(movies)-summary['coproduction_movies']}作品。Animationなしを実写確定とは解釈しない。", '',
             f"合作を含む条件により、WikidataのP495に日本がある『ブレット・トレイン』『NOPE/ノープ』『ソニック・ザ・ムービー』等も対象。合作への評価は正式抽出内で{sum(int(m['n_ratings_subset']) for m in movies if m['is_coproduction'] == 'true')}件。各作品の取得国集合をmovies.csvで確認できる。", '',
             f"正式作品年: {min(years) if years else 'なし'}〜{max(years) if years else 'なし'}。候補作品年: {min(int(m['movie_year']) for m in allmeta)}〜{max(int(m['movie_year']) for m in allmeta)}。原本評価: {scan['rated_at_utc_min']}〜{scan['rated_at_utc_max']}。正式評価: {min(final_dates) if final_dates else 'なし'}〜{max(final_dates) if final_dates else 'なし'}。", '',
             '原本READMEは収録終期を2023年10月12日と説明するが、UTC実測の最大timestampは2023年10月13日02:29:07。収録終期表記のタイムゾーンは確認できない。公式チェックサムは一致しており、別版と置き換えたり、12日を超えるUTC評価を切り捨てたりせず、この差を記録する。', '',
             f'収録終了年より先の候補作品年: {len(future)}作品。logs/years_after_collection_end.csvに記録。年上限フィルタは追加していない。', '',
             '## 分布と分析適性', '',
             markdown_table(['評価件数', '最小', '中央値', '最大'], [[label, *summary[key].values()] for label, key in [('ユーザー別', 'user_rating_counts'), ('作品別', 'movie_rating_counts')]]), '',
             markdown_table(['評価点', '件数'], sorted(summary['rating_distribution'].items())), '',
             f"行列密度: {density:.4%}。" if density is not None else '行列密度: 空集合のため計算不能。',
             f"二部グラフの連結成分: {graph['components']}。最大成分: {graph['largest']['users']}ユーザー・{graph['largest']['movies']}作品。連結していても各ユーザー対の共通評価が十分とは限らず、共通評価数の少ない類似度は不安定。", '',
             f"{len(ratings):,}評価を含む。件数と疎密を確認する導入演習、採点の甘辛、ユーザー平均を引いた嗜好比較に利用できる。作品の{sum(int(m['n_ratings_subset']) == 1 for m in movies)}件は評価1件で、標本標準偏差を計算できない。推薦実験は人気順・平均点の基準モデルから始め、共通評価数を併記した類似度を使う。評価数の少ない作品の予測と分散推定は不安定。分割後の各ユーザーの学習件数を確認し、時系列分割で情報漏洩を防ぐ。全期間集計列を予測特徴量に直接使わない。", '',
             markdown_table(['作品ペアの共通評価者数', 'ペア数'], [['全作品ペア', summary['item_pair_overlap']['total_pairs']], ['0人', summary['item_pair_overlap']['zero_overlap']], *[[f'{k}人以上', n] for k, n in summary['item_pair_overlap']['at_least'].items()]]), '',
             '年を広げて評価件数が増えても、作品数・ユーザー数も増えるため密度が上がるとは限らない。作品類似度の分析では共通評価者数と未推定ペアを併記し、未評価を0点で埋めない。', '',
             '## 評価件数の多い作品', '',
             markdown_table(['movieId', '作品', '件数', '平均', '標本標準偏差'], [[m['movieId'], m['title_ja'] or m['title'], m['n_ratings_subset'], f"{float(m['mean_rating_subset']):.3f}", f"{float(m['std_rating_subset']):.3f}" if m['std_rating_subset'] else '欠損'] for m in popular]), '',
             '## 評価が分かれる候補', '',
             '標本標準偏差の降順（分散と同じ順位）。2件以上の作品を掲載。少数評価で高順位になりやすく、安定した賛否の証拠ではない。', '',
             markdown_table(['movieId', '作品', '件数', '標本標準偏差'], [[m['movieId'], m['title_ja'] or m['title'], m['n_ratings_subset'], f"{float(m['std_rating_subset']):.3f}"] for m in divided]), '',
             '## 感度分析と改善案', '',
             f'作品年{year}以上と日本条件は固定。下表は比較集計のみで、正式CSVは5作品条件を維持。', '',
             markdown_table(['最低作品数', '作品', 'ユーザー', '評価'], [[s['min_target_movies_per_user'], s['movies'], s['users'], s['ratings']] for s in es['sensitivity']]), '',
             '改善はまず未照合・国欠損・複数候補の個別確認を行い、補正する場合は元値・補正値・根拠URL・確認日・理由をmetadata_overrides.csvへ保存する。日本語題名や監督国籍だけで日本作品にしない。次の別条件実験として最低3作品や他国を含む比較を検討できるが、この版には適用していない。MovieLensの2023年10月までという観測終期は変更できず、最近の作品ほど評価蓄積が少ない。', '',
             '## ファイルサイズ', '', markdown_table(['ファイル', 'bytes'], [*filesizes.items(), ['合計', sum(filesizes.values())]]), '',
             f"合計 {sum(filesizes.values())/1_000_000:.3f} MB (10進)、{sum(filesizes.values())/1048576:.3f} MiB。" + ('10 MB以内で授業用に扱いやすいサイズ。' if sum(filesizes.values()) <= 10_000_000 else '10 MBを超えるが切り捨てていない。'), '',
             '## 検証', '',
             markdown_table(['検査', '結果'], [[c['check'], '成功' if c['passed'] else '失敗'] for c in validation['checks']]), '',
             '原本ZIPの公式MD5、各CSVの公式MD5、ZIP CRCと展開パスを確認。32,000,204評価を逐次走査し、原本全体のID参照・評価値・userId×movieId一意性を確認。別走査で対象ユーザー集合と全評価の原本一致を検証。固定レスポンスキャッシュからメタデータを再構築し、3つのCSVのSHA-256一致を確認。詳細はlogs/validation.json。', '',
             '## 出典・利用条件', '', source_line,
             'MovieLens同梱READMEと公式HTML READMEの主要条件に矛盾なし。全文をlicenses/に保存。Wikidataの構造化追加データのみCC0。評価データを含む成果物全体はCC0ではない。コード用MITライセンスはデータ・統計・レポートには適用されない。公開・再配布時も原本の利用条件・出典を維持する。']
    (OUT / 'report.md').write_text(('\n'.join(lines) + '\n').replace('logs/', log_name + '/'), encoding='utf-8')
    compare_with_2020(summary, ratings, movies, users)
    # Inventory includes evidence and code; distributing only the small CSVs is insufficient for offline replay.
    inputs = [p for directory in [RAW, CACHE] for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.startswith('.') and not p.name.endswith(('.tmp', '.part'))]
    # Only extraction/reproduction code belongs to this dataset's provenance.
    # Unrelated local analysis scripts may be deliberately unpublished.
    inputs += [WORK / 'scripts' / name for name in
               ['pipeline.py', 'test_pipeline.py', 'prepare_publication.py']]
    inputs += [CONFIG_PATH, WORK / 'config.json', WORK / 'requirements.txt', ROOT / 'movielens_32m_subset_handoff.md']
    if year == 2015:
        inputs += [p for p in (ROOT / 'outputs/movielens_jp_2020_min5').glob('*.csv')]
        baseline_meta = WORK / 'logs/metadata_all_candidates.csv'
        if baseline_meta.exists():
            inputs.append(baseline_meta)
    inputs += [ROOT / name for name in ['README.md', 'LICENSE.md', 'LICENSE-CODE', '.gitignore'] if (ROOT / name).exists()]
    override = WORK / 'metadata_overrides.csv'
    if override.exists():
        inputs.append(override)
    inventory = {str(p.relative_to(ROOT)): {'sha256': digest(p), 'bytes': p.stat().st_size,
                                          'included_in_repository': not p.is_relative_to(RAW)} for p in sorted(inputs)}
    urls = [{'path': str(p.relative_to(ROOT)), **public_receipt(read_json(p))} for directory in [RAW, CACHE] for p in sorted(directory.rglob('*.http.json'))]
    commands = [{**c, 'cwd': '.', 'argv': [a.replace(str(ROOT) + '/', '') for a in c['argv']]}
                for c in (json.loads(line) for line in (LOG / 'commands.jsonl').read_text().splitlines())]
    manifest = {'dataset_name': f'MovieLens作品年{year}年以降・日本製作国を含む作品', 'generated_at_utc': utc(),
                'config': CFG, 'python_version': sys.version, 'platform': platform.platform(), 'dependencies': 'standard library only',
                'script_version': '1.2.1', 'input_inventory': inventory, 'retrievals': urls,
                'commands': commands,
                'distribution': {'raw_included': False, 'raw_acquisition': 'python3 work/movielens32m/scripts/pipeline.py download',
                                 'license_scope': 'LICENSE.md', 'code_license_applies_to_data': False},
                'manual_overrides': str(override.relative_to(ROOT)) if override.exists() else None,
                'validation': validation, 'summary': summary,
                'audit_inventory': {str(p.relative_to(ROOT)): {'sha256': digest(p), 'bytes': p.stat().st_size} for p in public_audit_files()}}
    save_json(OUT / 'manifest.json', manifest)
    paths = sorted(p for p in OUT.rglob('*') if p.is_file() and not p.name.startswith('.') and p.name != 'checksums.sha256')
    (OUT / 'checksums.sha256').write_text(''.join(f'{digest(p)}  {p.relative_to(OUT)}\n' for p in paths), encoding='utf-8')
    print(f'report complete: {OUT}; {sum(filesizes.values())} bytes CSV', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['download', 'metadata', 'extract', 'validate', 'report', 'all'])
    parser.add_argument('--offline', action='store_true', help='Never retrieve missing metadata; use frozen caches')
    parser.add_argument('--audit-ambiguities', action='store_true', help='Save full competing entities for diagnosis; never changes selection')
    parser.add_argument('--min-year', type=int, choices=[2015, 2020], default=2020, help='Use an isolated extraction profile; all other selection conditions stay fixed')
    args = parser.parse_args()
    configure(args.min_year)
    for path in [RAW, CACHE, LOG, OUT]:
        path.mkdir(parents=True, exist_ok=True)
    formal = {'dataset': 'ml-32m', 'min_movie_year': args.min_year, 'min_target_movies_per_user': 5,
              'year_source': 'movielens_title_suffix', 'country_source': 'wikidata_P495',
              'country_qid': 'Q17', 'include_coproductions': True, 'include_animation': True,
              'min_ratings_per_movie': None}
    require(all(CFG[k] == v for k, v in formal.items()),
            'This delivery preserves the selected year/min5/Japan definition; unsupported condition changes are refused')
    require(CFG['batch_size'] > 0 and CFG['max_attempts'] > 0, 'Invalid request settings')
    with open(LOG / 'commands.jsonl', 'a', encoding='utf-8') as f:
        f.write(json.dumps({'utc': utc(), 'argv': sys.argv, 'python': sys.version, 'cwd': str(Path.cwd())}) + '\n')
    stages = ['download', 'metadata', 'extract', 'validate', 'report'] if args.stage == 'all' else [args.stage]
    for stage in stages:
        if stage == 'metadata':
            metadata(args.offline)
            if args.audit_ambiguities:
                audit_ambiguities(args.offline)
        elif stage == 'download':
            download(args.offline)
        else:
            globals()[stage]()


if __name__ == '__main__':
    main()
