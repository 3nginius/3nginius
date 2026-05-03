# revsearch

Reverse video/image search pipeline.

```
URL or local file ──► yt-dlp ──► ffmpeg keyframes ──► pHash dedup ──► providers ──► hits
```

Built to take any video URL (anywhere `yt-dlp` works) or local image/video,
extract a small set of representative keyframes, deduplicate them by
perceptual hash, and submit them in parallel to one or more reverse-image
providers.

## Install

```bash
# system tools
sudo apt-get install -y ffmpeg
# python package (editable for hacking)
pip install -e .
```

`yt-dlp` is pulled in as a Python dependency, so the `yt-dlp` command becomes
available on PATH automatically.

## Usage

```bash
# list providers and which have credentials
revsearch --list-providers

# search a local video, free Yandex provider only
revsearch ./clip.mp4 --providers yandex

# search a URL (any yt-dlp-supported site), all available providers, JSON
revsearch "https://example.com/post/123" --format json

# pick the second video in a multi-video post
revsearch "https://example.com/post/123" --video-index 2

# tune frame extraction
revsearch ./clip.mp4 --max-frames 10 --scene-threshold 0.20
```

## Providers

| name                  | needs                                | notes                                          |
| --------------------- | ------------------------------------ | ---------------------------------------------- |
| `yandex`              | nothing                              | free; returns search URL + best-effort scrape  |
| `tineye`              | `TINEYE_API_KEY`                     | best for finding earlier copies of an image    |
| `google_lens_serpapi` | `SERPAPI_API_KEY`                    | uses SerpAPI's Google Lens engine              |
| `bing_visual`         | `BING_VISUAL_SEARCH_KEY`             | Azure Cognitive Services Bing Visual Search    |

`google_lens_serpapi` needs a publicly reachable image URL. By default it
uploads to `0x0.st`. To use your own host, set
`REVSEARCH_PUBLIC_BASE_URL=https://yourcdn.example.com/path`; the provider
will then assume the keyframe filename is reachable at that base.

## Output

Text mode prints a per-frame block with each provider's hits and any
openable search URL. JSON mode (`--format json`) emits the full structured
report — useful for piping into another tool.

## How it works

1. **Acquire** — `revsearch.downloader` either passes through a local path or
   shells out to `yt-dlp -f best[ext=mp4]/best --playlist-items N`.
2. **Frames** — `revsearch.frames` first tries ffmpeg scene-change detection
   (`select='gt(scene,T)'`); if too few frames are produced it falls back to
   evenly-spaced timestamps.
3. **Hash & dedupe** — `revsearch.hashing` computes pHash per frame and drops
   any frame within Hamming distance 6 of one already kept.
4. **Search** — each surviving frame is submitted in parallel (one thread
   per provider) via the `Provider` interface in `revsearch.providers.base`.

## Adding a provider

Subclass `revsearch.providers.base.Provider`, implement `is_available()` and
`search(image_path) -> SearchResult`, then register it in
`revsearch/providers/__init__.py::all_providers`.
