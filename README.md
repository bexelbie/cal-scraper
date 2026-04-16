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

## Development

```bash
# Run tests
pytest

# Run linter
ruff check .
```
