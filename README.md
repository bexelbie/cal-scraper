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

# Scrape multiple specific sites
cal-scraper --site hvezdarna vida

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

### Index Page

By default, each run generates an `index.html` alongside the `.ics` files. The
index lists every calendar found in the output directory — including files from
previous runs — with descriptions and subscribe links.

```bash
# Disable index generation
cal-scraper --no-index

# Use a custom HTML template
cal-scraper --index-template /path/to/my-template.html
```

The default template uses `string.Template` placeholders:

| Variable | Content |
|----------|---------|
| `$title` | Page heading (default: "Calendar Feeds") |
| `$subtitle` | Subheading (default: "iCal feeds scraped by cal-scraper") |
| `$calendars` | Auto-generated HTML blocks — one per `.ics` file |
| `$generated_at` | Timestamp of generation |

The index reads metadata directly from each `.ics` file's headers
(`X-WR-CALNAME`, `X-WR-CALDESC`, `X-CAL-SOURCE-URL`), so it always reflects
the full contents of the output directory regardless of which sites were
scraped in the current run. This supports incremental workflows — run Czech
feeds first, translated feeds second, and the index covers everything.

Source URLs embedded in calendar descriptions (via the `Source:` convention)
are stripped from the index display to avoid duplication, since they appear as
dedicated clickable links instead.
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

Output files: `moravska-galerie.ics`, `hvezdarna.ics`, `ikea-brno.ics`, `vida.ics`, `index.html`

With `--filename-suffix=-en`, .ics files become `moravska-galerie-en.ics`, etc.

### ICS Conventions

Each generated `.ics` file includes calendar-level properties that the index
generator (and other tools) can read:

| Property | Standard? | Purpose |
|----------|-----------|---------|
| `X-WR-CALNAME` | De facto (Apple/Google) | Calendar display name |
| `X-WR-CALDESC` | De facto (Apple/Google) | Calendar description shown by most clients |
| `X-CAL-SOURCE-URL` | Custom (ours) | Original venue URL that was scraped |

**Description format convention:** Calendar descriptions end with a
`Source: <url>` clause so that the URL is visible in calendar clients that
display `X-WR-CALDESC`. For example:

```
Unofficial scrape — kids events only. Source: https://www.ikea.com/cz/cs/stores/brno/
```

The index generator strips this trailing `Source: <url>` when rendering
`index.html` (using a regex match on the pattern) to avoid showing the URL
twice — once as description text and again as a clickable "Source website"
link read from `X-CAL-SOURCE-URL`. When adding new sites, follow this
convention so the stripping works automatically.

### Date Parsing

Moravská galerie event dates use Czech formatting (e.g. `23/5/2026, 13–22 H`).
The parser handles seven known patterns via regex — see `date_parser.py` for
the full list (DATE-01 through DATE-07).

**LLM fallback:** When no regex pattern matches, the parser falls back to
Azure OpenAI (if credentials are configured) to parse the date string into
structured JSON. This avoids silently dropping events when the gallery
introduces a new date format. The fallback:

- Reuses the same Azure OpenAI credentials as `--translate`
- Returns an empty list (same as today) when credentials are absent
- Logs at INFO level when the LLM successfully parses a date
- Is never called for known regex patterns (zero added latency for the common case)

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

Each run regenerates `index.html` by scanning the full output directory, so
the final index always lists both Czech and translated calendars.

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

Point a web server (nginx, caddy, etc.) at the output directory. The generated
`index.html` serves as a landing page listing all available calendars. Ensure
`*.ics` files are served with `Content-Type: text/calendar` for calendar app
subscriptions.

## Development

```bash
# Run tests
pytest

# Run linter
ruff check .
```
