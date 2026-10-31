# DASH-247 — Weekly location activity report

## Run locally

```
docker compose up -d --build
```

Then open <http://localhost:8000>. The app container applies the migration, loads the seed if the
database is empty, and starts the server.

## Run tests

```
docker compose run --rm app uv run --frozen pytest -q
```

Or locally, with a running database: `uv run pytest -q`.

## Stack and why

TODO

## Interpretation

TODO

## Decisions and trade-offs

TODO

## Known limitations

TODO

## Deferred / what I'd do with another day

TODO

## AI usage

TODO
