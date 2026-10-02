#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Remove unnecessary HTTP transport identifiers; preserve originals locally.

Response JSON, queries, source data, retrieval timestamps and SHA-256 values
remain unchanged. Run pipeline.py report afterwards to refresh inventories.
"""
import shutil

import pipeline as p


def main():
    count = 0
    for path in sorted(p.CACHE.rglob('*.http.json')):
        original = p.read_json(path)
        public = p.public_receipt(original)
        if public == original:
            continue
        backup = p.WORK / 'private_http_metadata' / path.relative_to(p.CACHE)
        if not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, backup)
        p.save_json(path, public)
        count += 1
    print(f'Prepared {count} public HTTP receipts; original receipts retained in ignored private_http_metadata/.')


if __name__ == '__main__':
    main()
