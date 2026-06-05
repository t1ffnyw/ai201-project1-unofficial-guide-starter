# raw/ — manually-saved Reddit JSON

Reddit hard-blocks unauthenticated programmatic access, so the 13 Reddit threads can't be
fetched by the scraper. Save them by hand once, then `scrape.py` parses them from here.

## How to save each thread

1. Make sure you're **logged into Reddit** in your browser.
2. Run `python scrape.py --reddit-urls` to print the exact `.json` URL for each thread.
3. For each one, open the `.json` URL in your browser and save the response as
   `raw/{id}.json` — e.g. thread #18 → `raw/18.json`.
   (In most browsers: open the URL, then File → Save Page As, or copy the JSON into the file.)
4. Re-run `python scrape.py`. Saved threads turn from `[skip]` into `[ok]` and produce
   `documents/{id}_{slug}.txt`.

Expected files: `01.json` … `09.json`, `16.json`, `17.json`, `18.json`, `19.json`.
