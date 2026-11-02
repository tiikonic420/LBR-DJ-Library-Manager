"""Synthetic references only; reproducible timings, no real music access."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Sources_application'))
from library_services import Catalogue
parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
report = {'python': sys.version, 'benchmarks': []}
with tempfile.TemporaryDirectory(prefix='lbr_benchmark_') as temp:
    for count in (1000, 10000, 100000):
        catalogue = Catalogue(Path(temp) / (str(count) + '.sqlite'))
        start = time.perf_counter()
        for first in range(0, count, 1000):
            catalogue.upsert([{'path': f'/synthetic/genre{i%20}/{i}.flac', 'title': f'Titre {i}', 'artist': f'Artiste {i%100}', 'album': 'Été Réunion', 'genre': f'Genre {i%20}', 'bpm': 80 + i % 90, 'year': 2000 + i % 27, 'key': f'{i%12+1}A', 'duration': 180 + i % 60, 'format': 'flac'} for i in range(first, min(first + 1000, count))])
        insertion = time.perf_counter() - start
        samples = []
        for _ in range(10):
            for query in ('titre 99', 'réunion', 'absent', 'artiste 12', '2026'):
                start = time.perf_counter()
                catalogue.search(query)
                samples.append((time.perf_counter() - start) * 1000)
        ordered = sorted(samples)
        p95 = ordered[int(.95 * (len(ordered) - 1))]
        row = {'references': count, 'insertion_seconds': insertion, 'search_median_ms': statistics.median(samples), 'search_p95_ms': p95, 'search_max_ms': max(samples), 'samples_ms': samples, 'target_ms': 150 if count <= 10000 else 500}
        row['target_met_on_this_host'] = p95 <= row['target_ms']
        report['benchmarks'].append(row)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps([{k: v for k, v in r.items() if k != 'samples_ms'} for r in report['benchmarks']], indent=2))
