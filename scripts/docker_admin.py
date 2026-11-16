"""Create one disposable local CISO Assistant superuser without printing its password."""
from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, "/code")
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ciso_assistant.settings")
django.setup()

from django.contrib.auth import get_user_model

email = "vad-local-admin@example.test"
credential_file = Path("/code/db/admin_credentials.txt")
User = get_user_model()

if credential_file.exists():
    print(json.dumps({"created": False, "email": email, "credential_file": str(credential_file)}))
else:
    password = secrets.token_urlsafe(32)
    user = User.objects.filter(email=email).first()
    if user is None:
        user = User.objects.create_superuser(email=email, password=password)
    else:
        user.set_password(password)
        user.is_superuser = True
        user.is_active = True
        user.keep_local_login = True
        user.save()
    credential_file.write_text(
        f"URL=https://localhost:8443\nEMAIL={email}\nPASSWORD={password}\n",
        encoding="utf-8",
    )
    credential_file.chmod(0o600)
    print(json.dumps({"created": True, "email": email, "credential_file": str(credential_file)}))
