# CLAUDE.md

Source for **ippsec.rocks**, a static search engine over IppSec's YouTube videos. A Python crawler pulls every video's description from the YouTube Data API. Each timestamped line ("chapter") becomes one searchable entry in `dataset.json`. The site searches that file in the browser and links each result to `youtube.com/watch?v=<id>&t=<seconds>`.

Hosted on **GitHub Pages** from `master` (`CNAME` → `ippsec.rocks`). There is no build step and no backend. Pushing to `master` deploys.

## Layout

| Path | Purpose |
|------|---------|
| `yt_crawl.py` | **The crawler.** Regenerates `dataset.json`. |
| `dataset.json` | Generated search index (~500 videos, ~9k timestamps, ~750KB, one line). Committed. Don't hand-edit it, and don't `Read` the whole thing; use `python3`/`jq`. |
| `index.html`, `logic.js` | The search page. Plain JS, no framework, no bundler. |
| `style.scss` → `style.css` | Styles (`themes/*.scss` are imported). Both files are committed. |
| `contributions/` | A separate "My Contributions" page with its own `contributions.csv` → `dataset.json` (via `csvToDb.py`), `logic.js` and styles. |
| `yt_data.py` | Old experimental copy of the crawler (it prints video durations and returns no entries). Not used, and it still writes the old flat format. |
| `test-cors.html` | Old copy of the index page. Not linked. |
| `holidayhack2016/` | Static Jekyll output from a 2016 SANS Holiday Hack writeup. Legacy; leave alone. |
| `sponsors/` | Banner images, shown in the commented-out `div.sponsor` block in `index.html`. |

## Updating the dataset

```sh
python3 yt_crawl.py -g -a <YOUTUBE_API_KEY>   # or put the key in ./yt.secret and omit -a
git push
```

- `-g` commits `dataset.json` with the message `Updated dataset`. Without it, commit by hand. `-o` writes somewhere else (handy for diffing against the current file).
- `yt.secret` is gitignored. Never commit an API key.
- The only dependency is `requests`.
- Each run uses YouTube API quota: one `playlistItems` call per 50 videos, plus the difficulty playlists.

### What the crawler does (`run()` in `yt_crawl.py`)

1. **Tags:** `GetPlaylistItems` reads every page of each playlist in `playlists` (linux/windows × easy/medium/hard/insane) and maps `title → tag`. Tags are matched by exact title.
2. **Videos:** it reads the channel's "uploads" playlist (from `channel_id`), newest first.
3. **Lines:** `ParseLine` turns each non-empty description line into `[seconds, text]`:
   - `01:23 - Running nmap`, `1:02:03 - ...` and `01:23 Running nmap` all parse (see `timestamp_re`). The separator dash is optional.
   - A line without a leading timestamp becomes `[0, line]`. That's why intro text, links and so on appear as results at the start of a video.

### `dataset.json` format

The file is grouped by video and written as compact JSON (`separators=(',',':')`, UTF-8):

```json
[{"id":"abc123","title":"HackTheBox - Lame","tag":"linux easy","lines":[[0,"Intro text"],[312,"Running nmap"]]}]
```

- `id` is the YouTube video ID.
- `tag` is `""` if the video isn't in a difficulty playlist.
- In `lines`, each `[t, text]` has `t` in seconds, used directly as `&t=` in the link.
- If you change this format, update both `yt_crawl.py` and the loader in `logic.js`.

## Front-end (`logic.js`)

- Loads `./dataset.json` with `fetch` on `DOMContentLoaded`. It flattens the file into `window.dataset`, one entry per line: `{machine, videoId, time, line, haystack}`. `haystack` is `(line + machine + tag).toLowerCase()`, computed once.
- It searches on every `input` event.
- Search builds a regex in which every space-separated word must match: `(?=.*word1)(?=.*word2)`. A word starting with `-` is excluded. It matches against `haystack`. User input is **not** regex-escaped, so characters like `(` or `+` act as regex syntax.
- `replaceStrings` strips the `HackTheBox - `, `VulnHub - ` and `UHC - ` prefixes from titles once, at load time.
- If there are more than `totalLimit` (250) results, it shows an error instead of rendering them.
- Rows are built by string replacement into `searchResultFormat` and inserted with `innerHTML`. Description text is trusted (it's the channel's own text) but not escaped.
- The page state is shown with body classes (`color-no-search`, `color-results-found`, `color-no-results`, `color-too-many-results`), which are styled in `themes/`.

## Local development

```sh
python3 -m http.server 8000   # fetch() needs http://, file:// won't work
```

**SCSS:** edit `style.scss` or `themes/*.scss`, then recompile to `style.css` and commit both. The original setup uses the VS Code Live Sass Compiler (`.vscode/settings.json`: expanded output, no source map). The CLI equivalent:

```sh
sass --no-source-map --style=expanded style.scss style.css
```

**Contributions page:** add a line to `contributions/contributions.csv` (`date;title;link;description`, `;`-separated, newest first). Then regenerate from inside that directory:

```sh
cd contributions && python3 csvToDb.py
```

## Conventions

- Keep it static: no build tooling, no frameworks, no npm. The site must keep working as plain files on GitHub Pages.
- Dataset refresh commits are just `Updated dataset`.
- There are no tests. To check a change, serve the site locally and try a few searches (e.g. `nmap`, `sqli -windows`, `linux hard`). Confirm the result links jump to the right second.
