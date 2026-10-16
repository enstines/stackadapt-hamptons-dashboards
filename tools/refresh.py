#!/usr/bin/env python3
"""Refresh every client dashboard from BigQuery.

  python3 tools/refresh.py              # all clients in clients.json
  python3 tools/refresh.py --group 495907

Runs the 12 dashboard queries (tools/queries.json) for each client, writes the results to a temp folder, checks
them, then rebuilds that client's page with make_client_page.py. A client whose queries fail keeps its old data.
Exit code is 1 if any client failed (so the scheduled run is flagged), after all other clients were refreshed.
Needs Google credentials (GOOGLE_APPLICATION_CREDENTIALS) with BigQuery Job User + Data Viewer.
"""
import argparse, datetime, decimal, json, math, os, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = 'stackadapt-reporting'
NAMES = ['totals', 'daily', 'campaigns', 'trackers', 'demographics', 'audiences',
         'domains', 'devices', 'geo', 'zip_shapes', 'counties', 'basemap']


def clean(v):
    if isinstance(v, decimal.Decimal):
        v = float(v)
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, bytes):
        return None
    return v


def run_query(client, sql):
    last = None
    for attempt in range(2):
        try:
            return [{k: clean(v) for k, v in dict(r).items()} for r in client.query(sql).result(timeout=600)]
        except Exception as e:  # retry once
            last = e
            time.sleep(10)
    raise last


def queries_for(group):
    if not str(group).isdigit():
        raise ValueError('campaign group id must be digits: %r' % group)
    qs = json.load(open(os.path.join(ROOT, 'tools', 'queries.json')))
    return {k: qs[k].replace('@@GROUP@@', str(group)) for k in NAMES}


def check(group, data):
    """Refuse to publish obviously broken results."""
    tot = [r for r in data['totals'] if r.get('campaign') == 'all']
    if not tot:
        raise RuntimeError('totals has no "all" row')
    if not data['campaigns']:
        raise RuntimeError('campaigns is empty')
    if not data['daily']:
        raise RuntimeError('daily is empty')


def refresh_group(client, group):
    data = {n: run_query(client, sql) for n, sql in queries_for(group).items()}
    check(group, data)
    with tempfile.TemporaryDirectory() as tmp:
        for n, rows in data.items():
            json.dump(rows, open(os.path.join(tmp, n + '.json'), 'w'), separators=(',', ':'))
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'make_client_page.py'), '--group', str(group), '--data', tmp], check=True)


def main(client=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--group')
    a = ap.parse_args()
    reg = json.load(open(os.path.join(ROOT, 'clients.json')))
    groups = [a.group] if a.group else list(reg)
    if client is None:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT)
    failed = []
    for g in groups:
        try:
            refresh_group(client, g)
            print('refreshed', g, reg.get(g, {}).get('name', ''))
        except Exception as e:
            failed.append(g)
            print('FAILED', g, '-', repr(e)[:400], file=sys.stderr)
    if failed:
        print('failed groups:', ', '.join(failed), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
