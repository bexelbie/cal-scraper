# Cal-Scraper

Scrapes Czech cultural venue websites in Brno and generates iCal (.ics) feeds.
Events are in Czech and are not translated — the .ics files preserve the original text.

**Supported sites:**

| Site | Key | What's scraped |
|------|-----|---------------|
| [Moravská galerie](https://moravska-galerie.cz/program/deti-a-rodiny/) | `moravska-galerie` | Children & family events |
| [Hvězdárna a planetárium Brno](https://www.hvezdarna.cz/) | `hvezdarna` | Public planetarium shows (school-only shows excluded) |
| [IKEA Brno](https://www.ikea.com/cz/cs/stores/brno/) | `ikea-brno` | Kids events (craft workshops, Småland activities) |

Each calendar is marked **(unofficial)** and includes a disclaimer — these are
not affiliated with the venues.

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
```

Output files: `moravska-galerie.ics`, `hvezdarna.ics`, `ikea-brno.ics`

## Development

```bash
# Run tests
pytest

# Run linter
ruff check .
```
