# CISO Assistant configuration records

The active verified setup is the full local Docker stack described in [docker/README.md](../docker/README.md). The current platform summary is [status.json](status.json), and [docker/status.json](../docker/status.json) records its version, services, checks and seeded records. Use the Docker instructions for the running web interface.

## Earlier native Windows configuration

This folder records an executed local CISO Assistant Community configuration for the Vendor Assurance Desk learning case. The upstream source is AGPL licensed outside its `enterprise/` tree; see `UPSTREAM-LICENSE.md` and `LICENSE-AGPL.txt`. Keep the upstream license and attribution with any redistribution. This project does not redistribute the upstream application clone or its environment.

## What was configured

The local SQLite database has one fictional supplier, one fictional cloud service, one entity assessment in `in_review`, and ten `AppliedControl` records in `to_do`. The controls come from `../case-study/control_catalog.json` and carry the review question, objective, expected evidence, proposed framework references, and mapping rationale. CISO Assistant's built-in NIST CSF 2.0 and ISO/IEC 27001:2022 libraries were loaded during upstream database initialization. All supplier names and evidence references are synthetic. No supplier evidence was actually reviewed. A framework reference is not a compliance or equivalence claim.

The exact result is recorded in `native-status.json`. The configuration script is idempotent and uses Django's ORM: `platform_seed.py`.

## Provenance and local setup

- Upstream repository: `https://github.com/intuitem/ciso-assistant-community`
- Checked out commit: `1f65dd3e23162c5d9da0efe83faf2d754a0205e8` (main snapshot; not tag v4.3.2)
- Runtime: Python 3.14, Django 6.1.2, isolated `backend/.venv`, local `platform/.tools/uv.exe`
- Database: `platform/state/ciso-assistant.sqlite3`
- Dependencies were resolved with upstream `uv sync --no-dev --python C:\Python314\python.exe`.
- Schema setup ran `python manage.py migrate --noinput --skip-checks`; the migration completed and upstream startup populated the local framework library.
- Migration and seed commands used process-scoped `SQLITE_FILE`, `ALLOWED_HOSTS=127.0.0.1,localhost`, `MAGIC`, `WEASYPRINT_DLL_DIRECTORIES`, and an MSYS2 UCRT64 DLL path. No machine-wide PATH or environment setting was made.
- Native Windows prerequisite packages installed into the pre-existing MSYS2 environment: `mingw-w64-ucrt-x86_64-file` and `mingw-w64-ucrt-x86_64-pango` plus their dependencies. This is a system-local change; it is not vendored here.

## Compatibility adaptation and limitations

`windows_compat.patch` is a narrow patch to upstream `backend/core/generators.py`: it guards the POSIX-only `resource` import and explicitly fails closed for the custom DOCX worker on Windows when POSIX memory limits are unavailable. It does not remove or bypass the memory limit. Keep `enterprise/` upstream code out of this project's distributable adapter.

The migrations used `--skip-checks` because native Windows system checks exercise optional integrations. A full Django system check, web server, and frontend were not verified as running; see `native-status.json`. Do not present this as a deployed or externally accessible platform. The database, dependency environment, and credentials/state directories are local and must not be committed. The SQLite database itself is intentionally excluded from the project package.

## Re-run seeding

From this directory, with the isolated backend environment active and `SQLITE_FILE` pointing to a local database:

```powershell
$env:SQLITE_FILE = (Join-Path $PWD 'state\ciso-assistant.sqlite3')
$env:ALLOWED_HOSTS = '127.0.0.1,localhost'
$env:MAGIC = 'C:\msys64\ucrt64\share\misc\magic.mgc'
$env:WEASYPRINT_DLL_DIRECTORIES = 'C:\msys64\ucrt64\bin'
$env:Path = 'C:\msys64\ucrt64\bin;' + $env:Path
$env:PYTHONUTF8 = '1'
& '.\ciso-assistant\backend\.venv\Scripts\python.exe' '.\platform_seed.py'
```

Only run against an isolated synthetic-data database. Bind any eventual development server to loopback and do not use real vendor data or credentials for this portfolio exercise.
