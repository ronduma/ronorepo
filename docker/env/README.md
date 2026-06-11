# docker/env

this directory contains environment configuration files for the docker compose setup.

## files

| file                   | tracked         | description                                                                                                                                  |
| ---------------------- | --------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `static.env`           | yes             | static config shared across all environments (internal ports, DB names, pgAdmin config). safe to commit - no user-specific or secret values. |
| `user.env`             | no (gitignored) | user-specific config (ports, UID, API keys). generated per-developer.                                                                        |
| `generate_user_env.sh` | yes             | script that generates `user.env` for the current user. run this on first setup.                                                              |

## first-time setup

run the generation script from the repo root to create your `user.env`:

```bash
./docker/env/generate_user_env.sh
```

this calculates port assignments based on your user ID and writes a `user.env` file to `docker/env/`. after generating, fill in any API keys (e.g. `OPENAI_API_KEY`).

## port assignment

- **UID ≤ 10000** (local dev): fixed ports - frontend `3000`, backend `8000`.
- **UID > 10000** (shared dev environment): ports are calculated from the UID to avoid collisions between users on the same machine.

## secrets

`user.env` is gitignored. never commit real API keys or credentials. if you need to add a new secret, add it to `generate_user_env.sh` as a placeholder line so other developers know to fill it in.
