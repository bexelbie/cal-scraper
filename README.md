# Cal-Scraper

Scrapes Czech cultural venue websites in Brno and generates iCal (.ics) feeds.
Events are in Czech by default — use `--translate` for bilingual English/Czech output.

**Supported sites:**

| Site | Key | What's scraped |
|------|-----|---------------|
| [Moravská galerie](https://moravska-galerie.cz/program/deti-a-rodiny/) | `moravska-galerie` | Children & family events |
| [Hvězdárna a planetárium Brno](https://www.hvezdarna.cz/) | `hvezdarna` | Public planetarium shows (school-only shows excluded) |
| [IKEA Brno](https://www.ikea.com/cz/cs/stores/brno/) | `ikea-brno` | Kids events (craft workshops, Småland activities) |
| [VIDA! Science Center](http://vida.cz/doprovodny-program) | `vida` | Family events & lab workshops (Brno area, no 18+ After Dark) |

Each calendar is marked **(unofficial)** and includes a disclaimer — these are
not affiliated with the venues. Events with estimated end times include a note
in the description.

## Installation

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# Scrape all sites, write .ics files to current directory
cal-scraper

# Scrape a specific site
cal-scraper --site hvezdarna

# Specify output directory
cal-scraper --output-dir /path/to/feeds

# Preview without writing files
cal-scraper --dry-run

# Skip detail page fetching (Moravská galerie only, faster but less info)
cal-scraper --site moravska-galerie --no-details

# Verbose logging
cal-scraper --verbose

# Translate to bilingual English/Czech (requires Azure OpenAI)
cal-scraper --translate
```

### Translation

The `--translate` flag uses Azure OpenAI (gpt-4o-mini) to produce bilingual events:
- **Title:** `English Title / Czech Title`
- **Description:** English text → event details → original Czech text

Set these environment variables:

```bash
export AZURE_OPENAI_ENDPOINT=https://YOUR-RESOURCE.openai.azure.com
export AZURE_OPENAI_KEY=your-api-key
export AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
export AZURE_OPENAI_API_VERSION=2025-01-01-preview
```

Output files: `moravska-galerie.ics`, `hvezdarna.ics`, `ikea-brno.ics`, `vida.ics`

With `--filename-suffix=-en`, files become `moravska-galerie-en.ics`, etc.

## Container Deployment

The project includes a `Containerfile` and systemd quadlet files for running
as a scheduled container on a Linux server.

### Build the container

```bash
podman build -t cal-scraper .
```

Or pull from GitHub Container Registry (after pushing to GitHub):

```bash
podman pull ghcr.io/bexelbie/cal-scraper:latest
```

### Set up systemd quadlet

1. Copy `cal-scraper.container` and `cal-scraper.timer` to your quadlet directory
   (e.g., `~/.config/containers/systemd/`)
2. Edit `cal-scraper.container`: adjust `Volume`, `Network`, and `EnvironmentFile` paths
3. Create the environment file from `cal-scraper.env.example` (only needed for translation)
4. Create the output directory (e.g., `mkdir -p ~/cal-scraper/feeds`)
5. Reload and enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now cal-scraper.timer
```

### What happens on each run

The container runs `cal-scraper` twice:
1. **Czech feeds** — all sites → `moravska-galerie.ics`, `hvezdarna.ics`, etc.
2. **Translated feeds** (if Azure env vars are set) — all sites → `moravska-galerie-en.ics`, etc.

On failure (site down, template changed, translation error):
- The failing site's file is **not overwritten** — the previous version stays
- Exit code 1 is returned so systemd records the failure
- A summary line is printed: `cal-scraper: 3/4 sites OK (failed: vida)`

### Monitoring

```bash
systemctl --user status cal-scraper.timer    # timer status
journalctl --user -u cal-scraper --no-pager -n 50  # recent logs
```

### Serving the feeds

Point a web server (nginx, caddy, etc.) at the output directory. Ensure `*.ics`
files are served with `Content-Type: text/calendar` for calendar app subscriptions.

## Development

```bash
# Run tests
pytest

# Run linter
ruff check .
```
