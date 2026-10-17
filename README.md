# hermes-plugin-supadata-extract

A [Hermes](https://github.com/NousResearch/hermes-agent) plugin: URL-to-Markdown extraction via [Supadata's web scrape API](https://docs.supadata.ai/web/scrape).

## What it does

Registers an extract-only `web_extract` provider backend (`provides_web_providers: [supadata]`).
One credit per page. Supadata's free pool is small (100 credits/month) and is shared with its
YouTube transcript API, so place this rung after larger free pools.

Designed as a rung of [resilient-search](https://github.com/sergattic/hermes-plugin-resilient-search)
(v1.1.0+), which calls it through Hermes' web provider registry and fails over to the next rung on
quota, rate-limit or upstream errors. It also works on its own as a `web.extract_backend`.

## Requirements

- `SUPADATA_API_KEY` in the environment.

## Config (`config.yaml`)

```yaml
secrets:
  onepassword:
    env:
      SUPADATA_API_KEY: op://<your-vault>/<item>/<field>
```

## Install

```
hermes plugins install sergattic/hermes-plugin-supadata-extract
```

## Tests

```
pip install pytest httpx
python -m pytest -q tests
```

The tests stub Hermes' `agent.web_search_provider` module, so they run without Hermes installed.

## License

MIT
