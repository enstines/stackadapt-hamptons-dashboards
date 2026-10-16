#!/usr/bin/env python3
"""Create or refresh one client dashboard page.

  python3 tools/make_client_page.py --group 495907 --data DIR_WITH_12_JSON_FILES [--name "Client name"]

- Looks the group up in clients.json (repo root); a new group gets a fresh random link code.
- Copies the data files into site/r/<code>/data/ and writes site/r/<code>/index.html from tools/client_template.html.
- Never touches other clients' folders.
"""
import argparse, json, os, re, secrets, shutil, sys

DATASETS = ['totals', 'daily', 'campaigns', 'trackers', 'demographics', 'audiences',
            'domains', 'devices', 'geo', 'zip_shapes', 'counties', 'basemap']
ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789'   # no look-alike characters

ap = argparse.ArgumentParser()
ap.add_argument('--group', required=True)
ap.add_argument('--data', required=True)
ap.add_argument('--name')
a = ap.parse_args()

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
reg_path = os.path.join(root, 'clients.json')
reg = json.load(open(reg_path)) if os.path.exists(reg_path) else {}

camp = json.load(open(os.path.join(a.data, 'campaigns.json')))
group_name = a.name or (camp[0].get('campaign_group') if camp else None) or ('Campaign group ' + a.group)

entry = reg.get(a.group)
if not entry:
    code = ''.join(secrets.choice(ALPHABET) for _ in range(10))
    entry = reg[a.group] = {'code': code}
entry['name'] = group_name
try:
    tot = json.load(open(os.path.join(a.data, 'totals.json')))
    entry['last_day'] = next((t.get('last_day') for t in tot if str(t.get('campaign')) == 'all'), None)
except Exception:
    pass
code = entry['code']

out = os.path.join(root, 'site', 'r', code)
os.makedirs(os.path.join(out, 'data'), exist_ok=True)
for d in DATASETS:
    src = os.path.join(a.data, d + '.json')
    if not os.path.exists(src):
        sys.exit('missing dataset file: ' + src)
    shutil.copyfile(src, os.path.join(out, 'data', d + '.json'))

tpl = open(os.path.join(root, 'tools', 'client_template.html'), encoding='utf-8').read()
tpl = re.sub(r'src="((?:icons|world)-\d+\.js)"', r'src="/assets/\1"', tpl)
esc = group_name.replace('&', '&amp;').replace('<', '&lt;')
page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>{esc} – Campaign Dashboard</title>
<link rel="stylesheet" href="/assets/theme.css">
<script src="/assets/d3.min.js"></script>
<script>window.DASH_DATASETS = {json.dumps(DATASETS)}; window.DASH_INITIAL_PARAMS = {{ group: {json.dumps(a.group)} }};</script>
<script src="/assets/dash-shim.js" data-base="./data/"></script>
</head>
<body>
<div id="app">
{tpl}
</div>
</body>
</html>
'''
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(page)
json.dump(reg, open(reg_path, 'w'), indent=2)
print('wrote site/r/%s/  (%s)' % (code, group_name))
if os.path.exists(os.path.join(root, 'site', 'home.json')):
    sys.path.insert(0, os.path.join(root, 'tools'))
    import make_home
    h = json.load(open(make_home.HOME)); make_home.rebuild(h)
    json.dump(h, open(make_home.HOME, 'w'), separators=(',', ':'))
    print('home page list updated')
