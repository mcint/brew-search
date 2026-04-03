# brew-hop-search

Fast offline-first search of Homebrew formulae, casks, taps, and installed packages.

Built on SQLite + FTS5 for instant local search with smart caching.

[GitHub](https://github.com/mcint/brew-hop-search) ·
[PyPI](https://pypi.org/project/brew-hop-search/) ·
[Brew Tap](https://github.com/mcint/homebrew-brew-hop-search/blob/main/Formula/brew-hop-search.rb)

## Install

```sh
# PyPI (recommended)
uv tool install brew-hop-search     # or: pip install brew-hop-search
uvx brew-hop-search python          # one-shot without install

# Homebrew tap
brew tap mcint/brew-hop-search
brew install brew-hop-search
```

## Usage

```sh
brew-hop-search <query>                  # search formulae + casks (default)
brew-hop-search -f <query>               # formulae only
brew-hop-search -c <query>               # casks only
brew-hop-search -i <query>               # search installed packages
brew-hop-search -t <query>               # also search tapped repos
brew-hop-search -L <query>               # search brew's local API cache (offline)
brew-hop-search -C                       # show cache status
brew-hop-search --refresh <query>        # force re-fetch before searching
```

### Cache control (bkt-style TTLs)

```sh
brew-hop-search --stale 1h <query>       # background refresh if cache > 1h old
brew-hop-search --fresh 24h <query>      # force sync refresh if cache > 24h old
```

### Output formats

```sh
brew-hop-search --json <query>           # JSON output
brew-hop-search -g <query>               # greppable: slug\tversion\turl
brew-hop-search -C --json                # machine-readable cache status
```

### Direct DB access

The SQLite database is at `~/.cache/brew-hop-search/brew-hop-search.db` and is fully compatible with [sqlite-utils](https://sqlite-utils.datasette.io/):

```sh
sqlite-utils tables ~/.cache/brew-hop-search/brew-hop-search.db
sqlite-utils search ~/.cache/brew-hop-search/brew-hop-search.db formula python
sqlite-utils query ~/.cache/brew-hop-search/brew-hop-search.db "SELECT name, desc FROM installed_formula"
```

## How it works

On first run, `brew-hop-search` fetches the Homebrew formula and cask indexes from `formulae.brew.sh`, stores them in a local SQLite database with FTS5 full-text search, and keeps the raw JSON alongside for easy re-creation.

Subsequent searches are instant (local FTS5 queries). Stale caches trigger a background refresh so the next search is both fast and fresh.

| Source | Flag | Data |
|--------|------|------|
| Remote API | *(default)* | `formulae.brew.sh` formula + cask indexes |
| Installed | `-i` | `brew info --json=v2 --installed` |
| Taps | `-t` | `.rb` files in `$(brew --repo)/Library/Taps/` |
| Local | `-L` | Brew's own API cache at `$(brew --cache)/api/` |

## License

MIT
