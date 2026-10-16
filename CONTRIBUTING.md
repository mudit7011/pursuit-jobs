# Contributing to Pursuit

Thanks for helping. Bug reports, fixes for job boards that changed their pages, and new form adapters are the most useful contributions.

## Before you start

- For anything bigger than a small fix, open an issue first so we can agree on the approach.
- Never commit your `.env`, `config/profile.json`, `sessions/`, `data/` or your resume. They're in `.gitignore`; keep it that way.
- Don't paste real personal data or session cookies into issues. Replace them with placeholders.

## Setting up

Follow [Getting started](README.md#getting-started) in the README. Then run the tests:

```bash
JAC_HEADLESS=1 python -m pytest tests
cd dashboard && npx tsc --noEmit
```

## Making changes

- Keep pull requests focused on one thing.
- Add or update tests for behaviour you change. Form handling is tested against saved HTML in `tests/fixtures/forms/`; add a fixture when you fix a new kind of form.
- Match the style of the code around your change.
- The bot must never invent facts about the user, never solve captchas and never submit without approval unless the user turned that on. Changes that weaken any of these won't be merged.

## Commit messages

One line, in the imperative, saying what changed: `fix instahyre apply button selector`.

## Reporting a broken job board

Open an issue with the site, what you expected, what happened, and the relevant lines from `logs/applications.log` with personal details removed.
