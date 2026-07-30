# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single Python/Flask web app (교안변환툴 / "lesson conversion tool"). It takes a CrayonSchool lesson URL (or a pasted lesson card) and generates an HTML preview by injecting parsed lesson data into the fixed player shell `crayon_shell.html`. There is no database, cache, or queue — it is one process.

### Running the app
- Dev server: `python3 app.py` — serves on `http://127.0.0.1:5055` (link-conversion UI at `/`, card→preview desk at `/desk`, health at `/health`). See `README.md`.
- The server binds to `127.0.0.1` only and runs with `debug=False` (no auto-reload). Restart the process manually to pick up code changes.

### Testing / lint / build
- There is no test suite, no linter config, and no build step in this repo. "Build" happens at runtime by generating preview HTML.
- Quick end-to-end check without a browser:
  - `curl http://127.0.0.1:5055/health` → `{"ok": true}`
  - `POST /api/card-to-preview` with `{"card": "...", "fetchImages": false}` works fully offline (no network needed).
  - `POST /api/convert` with a `crayonschool.co.kr` lesson URL requires outbound internet egress to `crayonschool.co.kr`.

### Gotchas
- Live URL conversion (`/api/convert`) and card image-enrichment (`fetchImages: true`) make outbound HTTP calls to `crayonschool.co.kr`. If egress is blocked, use the card path with `fetchImages: false` to test offline.
- The player template `crayon_shell.html` must contain the `__LESSON_DATA__` placeholder; `build_html()` raises if it is missing.
- `포털실행.bat` is a Windows-only launcher (not usable on Linux); it just runs `python app.py`.
