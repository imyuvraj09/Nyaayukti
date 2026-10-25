"""Create a consistent three-service local configuration without overwriting it."""

import argparse
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--frontend-port", type=int, default=5173)
parser.add_argument("--backend-port", type=int, default=3000)
parser.add_argument("--rag-port", type=int, default=8000)
args = parser.parse_args()
ports = [args.frontend_port, args.backend_port, args.rag_port]
if len(set(ports)) != 3 or any(not 1024 <= n <= 65535 for n in ports):
    parser.error("Use three different ports between 1024 and 65535.")
paths = [ROOT / name / ".env" for name in ("backend", "rag-service", "frontend")]
if any(path.exists() for path in paths):
    raise SystemExit(
        "Configuration already exists. No files changed. Edit the three .env files using their examples."
    )
token = secrets.token_urlsafe(48)
replacements = {
    "RAG_SERVICE_TOKEN": token,
    "RAG_SERVICE_URL": f"http://127.0.0.1:{args.rag_port}",
    "FRONTEND_URL": f"http://localhost:{args.frontend_port}",
    "FRONTEND_PORT": str(args.frontend_port),
    "BACKEND_PROXY_URL": f"http://127.0.0.1:{args.backend_port}",
}
for path in paths:
    content = path.with_name(".env.example").read_text(encoding="utf-8")
    lines = []
    for line in content.splitlines():
        key = line.split("=", 1)[0]
        if key == "PORT":
            line = f"PORT={args.backend_port if path.parent.name == 'backend' else args.rag_port}"
        elif key in replacements:
            line = f"{key}={replacements[key]}"
        lines.append(line)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
print(
    "Created matching local configuration. Set the model and API key in rag-service/.env, then run npm run check:setup."
)
