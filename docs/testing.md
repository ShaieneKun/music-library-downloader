# Testing

Tests use the standard library `unittest` and live in `src/tests/`. Task runner: [just](https://github.com/casey/just) (`brew install just`).

| Command | What it does |
| --- | --- |
| `just test` | Builds the `Containerfile` and runs **all** tests in a container (Python 3.14). Image tag: `music-library-downloader-test`. |
| `just test-compose` | Runs `src/tests/test_compose.py` on the **host** via `uv run --no-project` (Python from `.python-version`). Needs the `docker` CLI. |

Without just: `uv run python -m unittest discover -s src/tests -t .`

## Notes

- `test_compose.py` checks the `MUSIC_DIR` bind mount (default, override, `.env`, precedence, empty value, `create_host_path`, state volume stays named) in `compose.yaml` and `compose.debug.yaml` by running `docker compose config` in a temp directory with a fake `HOME`. It never touches the real `.env` or starts containers.
- Those tests skip themselves when `docker compose` is missing, which is why they are skipped inside the `just test` container; run `just test-compose` for them.
- The system Python on macOS is 3.9 and cannot import the project (needs 3.14+); always use `uv run` or the container.
- When changing the compose files, update `test_compose.py` too.
