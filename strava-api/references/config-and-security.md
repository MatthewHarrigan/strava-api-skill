# Config and Security

## Default config path

- `~/.strava.json`

## Override path

- Set `STRAVA_CONFIG=/absolute/path/to/config.json`

## Required keys

- `client_id`
- `client_secret`
- `refresh_token`

## Optional/managed keys

- `access_token`
- `expires_at`
- `athlete_id`

## Security rules

- Never commit `.strava.json` to git.
- Keep file mode `600`.
- Never print or return tokens in command output.
- Refresh tokens at runtime; do not hardcode access tokens in scripts.
