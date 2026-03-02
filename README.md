# script-runner

A lightweight Flask API that runs Python media mover scripts on demand and reports their status. Designed to be triggered by the [Script Runner UI](https://github.com/Treyzer567/landing-page) hosted on the landing page, which is embedded as an iframe panel in Homarr.

---

## How It Works

1. The frontend UI sends a `POST /run/<script-name>` request
2. The runner spawns the script in a background thread and returns a `job_id`
3. The UI polls `GET /status/<job_id>` until the job completes
4. Result (success/failed) and finish time are returned and cached in the browser

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/run/<script>` | Triggers a script by name. Returns a `job_id` |
| `GET` | `/status/<job_id>` | Returns job status (`running`, `success`, `failed`), start/end timestamps |
| `GET` | `/logs/<job_id>` | Returns raw stdout/stderr log output for a job |

Scripts are resolved by name from the `/scripts` directory — e.g. `POST /run/show-mover` runs `/scripts/show-mover.py`.

---

## Deployment

Runs as a Docker container defined in `landing-compose.yml` in the [landing-page](https://github.com/Treyzer567/landing-page) repo.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SONARR_URL` | Internal URL of your Sonarr instance (passed through to scripts) |
| `SONARR_API_KEY` | Sonarr API key (passed through to scripts) |

### Volume Mounts

| Container Path | Description |
|---------------|-------------|
| `/scripts` | Directory containing the `.py` scripts to run |
| `/logs` | Output directory for per-job log files |

Source and destination media paths also need to be mounted depending on which scripts you're running. See `landing-compose.yml` for the full volume list.

---

## Related Repos

| Repo | Description |
|------|-------------|
| [landing-page-simple](https://github.com/Treyzer567/landing-page) | Frontend hub — hosts the Script Runner UI iframe |
| [scripts](https://github.com/Treyzer567/scripts) | The actual Python mover scripts this runner executes |
