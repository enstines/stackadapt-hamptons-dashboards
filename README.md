# Client dashboards (static site)

One Render static site that serves every client's campaign dashboard.

- Each client gets an unguessable link: `https://<your-site>.onrender.com/r/<code>/`
- The site root (`/`) shows the logo and a password box. After you enter the password it lists every client dashboard with Open and Copy link buttons. The list is stored encrypted (`site/home.json`), so nobody without the password can read it. `robots.txt` blocks search engines.
- `clients.json` maps each StackAdapt campaign group id to its link code. It sits outside `site/`, so it is **not** published. Keep this repository private.

## Layout

```
render.yaml                 Render Blueprint (static site, publish dir ./site)
clients.json                group id -> link code + name (private)
site/index.html             password-protected home page (lists all dashboards)
site/home.json              the encrypted client list + the password-locked key (safe to publish)
site/assets/                d3, theme, dash-shim.js (stand-in for the Claude Dashboard runtime), site icons, world outlines
site/r/<code>/index.html    one client's dashboard page
site/r/<code>/data/*.json   that client's data (12 files, refreshed daily)
tools/client_template.html  the dashboard page
tools/make_client_page.py   create or refresh one client page from 12 data files (also updates the home list)
tools/refresh.py            pulls fresh data from BigQuery for every client in clients.json (run daily by GitHub)
tools/queries.json          the 12 dashboard queries
.github/workflows/refresh.yml   the daily schedule (copy in tools/refresh.yml if the hidden folder doesn't upload)
tools/make_home.py          set or change the home-page password (--setup), or rebuild the list (no password needed)
```

## Add or refresh a client

```
python3 tools/make_client_page.py --group <campaign_group_id> --data <folder with the 12 data json files>
git add -A && git commit -m "Update dashboards" && git push
```

Render redeploys automatically on every push.

The 12 data files (`totals, daily, campaigns, trackers, demographics, audiences, domains, devices, geo, zip_shapes, counties, basemap`) are the saved results of the dashboard queries for that campaign group.

## Home page password

The list is encrypted with a public key, so adding clients never needs the password. To change the password run `python3 tools/make_home.py --setup --force` (prints the new random password, or pass `--password "..."`), then commit and push. Use a long password: anyone can download `home.json` and try guesses offline.

## Daily refresh (GitHub Actions)

Every day at about 11:15 AM Eastern, GitHub runs `tools/refresh.py`, which re-runs the dashboard queries for each client in `clients.json`, rewrites that client's data, and commits the change. Render redeploys on that commit. You can also run it by hand: repo > Actions > "Refresh dashboards" > Run workflow.

Only clients already in `clients.json` are refreshed, so a new campaign group never gets a public page by accident. A client whose queries fail keeps its old data, and the run shows a red X (GitHub emails you).

### One-time setup: Google service account

1. Open https://console.cloud.google.com and pick the project `stackadapt-reporting` in the project picker (top left).
2. Menu > IAM & Admin > Service Accounts > **Create service account**. Name: `dashboard-refresh`. Click Create and continue.
3. Add two roles: **BigQuery Job User** and **BigQuery Data Viewer**. Continue, then Done.
4. Click the new account > **Keys** tab > Add key > Create new key > **JSON** > Create. A `.json` file downloads.
5. In this GitHub repo: Settings > Secrets and variables > Actions > **New repository secret**. Name: `GCP_SA_KEY`. Value: paste the entire contents of the JSON file. Save.
6. Delete the downloaded JSON file from your computer.
7. Repo > Actions > "Refresh dashboards" > Run workflow, and check that it finishes green.

If step 4 says key creation is disabled, your organization blocks service account keys; ask your Google Cloud admin to create the key or change that policy.
