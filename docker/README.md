# Local CISO Assistant Community stack

This optional local stack runs the upstream CISO Assistant Community images for the synthetic HarborPay Demo TPRM case. It is separate from the native Windows platform snapshot. The container image is CISO Assistant Community **v4.3.2** (image build `be43dc61e336c557e975d943d4c88c7dc4825ae1`); the cloned source tree commit is recorded separately in `status.json`.

The verification snapshot used Docker Engine `29.1.3` and Compose `2.40.3` in the existing Ubuntu 24.04 WSL2 distro. One-time WSL setup, if needed:

```powershell
wsl -d Ubuntu-24.04 -u root -- apt-get update
wsl -d Ubuntu-24.04 -u root -- apt-get install -y docker.io docker-compose-v2
wsl -d Ubuntu-24.04 -u root -- systemctl enable --now docker
```

`compose.override.yml` pins the backend, frontend, Caddy and Qdrant images to the digests recorded in `status.json`. The Compose configuration comes from the cloned CISO Assistant Community repository at commit `1f65dd3e23162c5d9da0efe83faf2d754a0205e8`; the running image build revision is separately reported above.

On a fresh checkout of this project, create the ignored upstream clone once from the repository root:

```powershell
git clone --no-checkout https://github.com/intuitem/ciso-assistant-community.git platform/ciso-assistant
git -C platform/ciso-assistant checkout --detach 1f65dd3e23162c5d9da0efe83faf2d754a0205e8
```

An existing clone should be inspected before changing its checkout. The wrapper expects the `Ubuntu-24.04` WSL distro, a running Docker service, and a repository on a Windows drive accessible through `/mnt/`. `Up` creates the named database volume when it is absent. The optional upstream MCP service is not started by these commands.

## Start and use

From the repository root in PowerShell:

```powershell
.\scripts\docker_ciso.ps1 -Action Up
.\scripts\docker_ciso.ps1 -Action Seed
.\scripts\docker_ciso.ps1 -Action Admin
.\scripts\docker_ciso.ps1 -Action Test
.\scripts\docker_ciso.ps1 -Action Status
```

Open <https://localhost:8443>. The generated local administrator credentials are written to the ignored, access-restricted file `docker/runtime/.private/admin_credentials.txt`. Do not commit or share that file. The application uses an internally generated TLS certificate, so a browser warning is expected for this local-only instance.

The first `Up` can take 20 minutes or more while the upstream backend runs schema migrations and imports its bundled libraries. The script starts the backend without waiting on Compose's shorter first-boot health retry window, polls health for up to 40 minutes, then starts the frontend, worker, and reverse proxy. A hidden WSL keepalive process maintains the Ubuntu 24.04 systemd-backed Docker service across command invocations; `-Action Stop` stops that matching process after stopping Compose.

The database, Caddy state, and Qdrant data use named Docker volumes in WSL's Linux filesystem, not bind mounts on Windows drvfs. This is required for the upstream image's ownership and permission behavior. The synthetic seed JSON and seed helper are staged in the database volume; all are ignored runtime data. Docker runtime data is not part of the GitHub source publication.

Authenticated UI evidence for the synthetic entity is published at [`output/ciso_entities.png`](../output/ciso_entities.png). The local credential file and working screenshots remain private and ignored.

## Network and data boundaries

- CISO Assistant is served on `127.0.0.1:8443`; Qdrant is on `127.0.0.1:6333`. Backend and worker ports are internal to the Compose network.
- The stack uses the AGPL-3.0 Community edition. It does not include Enterprise features.
- HarborPay Demo, its payroll service, evidence references, assessment, tier, and controls are fictional training data. The assessment remains `in_review`; seeded controls remain `to_do`. Framework references are proposed mappings, not audit results, certification, compliance determination, or evidence of an actual supplier.
- `-Action Stop` stops containers but retains named data volumes. Do not use `docker compose down -v` unless intentionally deleting this local database and application state.

## Repeatable checks

`-Action Test` checks the backend health endpoint, Django system checks, TPRM migrations, the HTTPS frontend route through Caddy, and Qdrant's local API. The expected Caddy root response is a redirect to the login screen (HTTP 302); the backend and Qdrant checks return HTTP 200. `status.json` records the verified test results and image digests for this run.
