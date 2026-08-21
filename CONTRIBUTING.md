# Contributing to CROSSLIST

Thanks for helping improve CROSSLIST. Bug reports, focused fixes, tests, and
documentation improvements are welcome.

## Before opening a pull request

1. Open an issue for substantial changes so the approach can be discussed.
2. Keep each pull request focused on one change.
3. Do not commit API credentials, developer tokens, or local `.env` files.
4. Add or update tests when behavior changes.

## Backend development

Set up the Python environment from the repository root:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Run the backend tests with:

```bash
cd backend
PYTHONPATH=. python -m pytest -q
```

## Swift development

Run the platform-neutral Swift tests with:

```bash
cd ios/CROSSLISTCore
swift test
```

For iOS app changes, open `ios/CROSSLIST.xcodeproj` in Xcode and build the
`CROSSLIST` scheme for an iOS simulator or a configured physical device.

## Pull request checklist

- Explain what changed and why.
- Include the commands used to verify the change.
- Confirm that the GitHub Actions checks pass.
- Call out any configuration, privacy, or security impact.
