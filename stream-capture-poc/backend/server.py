"""Local-only API for synthetic ChatGPT stream-capture experiments."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

ROOT = Path(__file__).resolve().parent


def load_env() -> dict[str, str]:
    result: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
    result.update({key: value for key, value in os.environ.items() if key in {
        "APP_HOST", "APP_PORT", "DATABASE_PATH", "LAB_API_TOKEN", "MAX_RESPONSE_CHARS", "RETENTION_DAYS"
    }})
    return result


CONFIG = load_env()
HOST = CONFIG.get("APP_HOST", "127.0.0.1")
PORT = int(CONFIG.get("APP_PORT", "8765"))
DB_PATH = (ROOT / CONFIG.get("DATABASE_PATH", "./data/stream-captures.sqlite3")).resolve()
TOKEN = CONFIG.get("LAB_API_TOKEN", "")
MAX_TEXT = min(200_000, int(CONFIG.get("MAX_RESPONSE_CHARS", "100000")))
RETENTION_DAYS = max(1, min(30, int(CONFIG.get("RETENTION_DAYS", "7"))))
MAX_BODY = MAX_TEXT * 4 + 50_000
ADAPTER_COMPATIBILITY = re.compile(r"^0\.1\.\d{1,3}$")


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS stream_captures (
      capture_id TEXT PRIMARY KEY,
      payload_hash TEXT NOT NULL,
      platform TEXT NOT NULL,
      path TEXT NOT NULL,
      request_id INTEGER,
      status_code INTEGER NOT NULL,
      content_type TEXT NOT NULL,
      capture_status TEXT NOT NULL,
      response_text TEXT NOT NULL,
      bytes INTEGER,
      chunks INTEGER,
      frames INTEGER,
      done_markers INTEGER,
      protocol_done INTEGER NOT NULL,
      reader_done INTEGER NOT NULL,
      truncated INTEGER NOT NULL,
      stream_elapsed_ms INTEGER,
      event_types_json TEXT NOT NULL,
      event_shapes_json TEXT NOT NULL,
      event_sequence_json TEXT NOT NULL,
      observed_at TEXT NOT NULL,
      received_at TEXT NOT NULL
    )""")
    columns = {row["name"] for row in db.execute("PRAGMA table_info(stream_captures)")}
    if "capture_status" not in columns:
        db.execute("ALTER TABLE stream_captures ADD COLUMN capture_status TEXT NOT NULL DEFAULT 'complete'")
    if "reader_done" not in columns:
        db.execute("ALTER TABLE stream_captures ADD COLUMN reader_done INTEGER NOT NULL DEFAULT 1")
    cutoff = datetime.now(timezone.utc).timestamp() - RETENTION_DAYS * 86400
    db.execute("DELETE FROM stream_captures WHERE julianday(received_at) < julianday(?)", (datetime.fromtimestamp(cutoff, timezone.utc).isoformat(),))
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def validate(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("JSON deve ser um objeto")
    expected = {"capture_id", "platform", "path", "request_id", "status_code", "content_type", "capture_status", "response_text",
                "bytes", "chunks", "frames", "done_markers", "protocol_done", "reader_done", "truncated", "stream_elapsed_ms",
                "event_types", "event_shapes", "event_sequence", "observed_at", "adapter_version"}
    if set(payload) != expected:
        raise ValueError("Campos do snapshot inválidos")
    try:
        capture_id = str(UUID(payload["capture_id"]))
        observed = datetime.fromisoformat(payload["observed_at"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError
        observed = observed.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Identificador ou horário inválido") from None
    if payload["platform"] != "chatgpt_web" or payload["path"] != "/backend-api/f/conversation":
        raise ValueError("Plataforma ou endpoint não permitido")
    if payload["status_code"] != 200 or payload["content_type"] != "text/event-stream":
        raise ValueError("Resposta não corresponde ao stream esperado")
    text = payload["response_text"]
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise ValueError("Texto da resposta inválido ou acima do limite")
    if payload["capture_status"] not in {"complete", "incomplete"}:
        raise ValueError("Status da captura inválido")
    if type(payload["protocol_done"]) is not bool or type(payload["reader_done"]) is not bool or type(payload["truncated"]) is not bool:
        raise ValueError("Indicadores de conclusão inválidos")
    if payload["capture_status"] == "complete" and (not payload["protocol_done"] or payload["truncated"]):
        raise ValueError("Captura completa precisa de estado final e não pode estar truncada")
    if payload["capture_status"] == "incomplete" and payload["protocol_done"]:
        raise ValueError("Captura incompleta não pode declarar estado final")
    if not isinstance(payload["adapter_version"], str) or not ADAPTER_COMPATIBILITY.fullmatch(payload["adapter_version"]):
        raise ValueError("Versão do adapter incompatível")
    limits = {"request_id": 2**53 - 1, "status_code": 599, "bytes": MAX_BODY, "chunks": 100_000,
              "frames": 100_000, "done_markers": 1000, "stream_elapsed_ms": 180_000}
    for key, limit in limits.items():
        value = payload[key]
        if value is not None and (type(value) is not int or value < 0 or value > limit):
            raise ValueError(f"Métrica inválida: {key}")
    safe_label = re.compile(r"^[a-zA-Z0-9_.:=-]{1,200}$")
    for key in ("event_types", "event_shapes", "event_sequence"):
        values = payload[key]
        if not isinstance(values, list) or len(values) > 32 or not all(isinstance(x, str) and safe_label.fullmatch(x) for x in values):
            raise ValueError(f"Resumo inválido: {key}")
    clean = {key: payload[key] for key in expected if key != "observed_at"}
    clean["capture_id"] = capture_id
    clean["observed_at"] = observed
    clean["payload_hash"] = hashlib.sha256(json.dumps(clean, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return clean


def token_matches(header: str) -> bool:
    return bool(TOKEN) and hmac.compare_digest(header, f"Bearer {TOKEN}")


def store_capture(capture: dict) -> tuple[int, dict]:
    received = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        existing = db.execute("SELECT payload_hash FROM stream_captures WHERE capture_id=?", (capture["capture_id"],)).fetchone()
        if existing:
            if existing["payload_hash"] != capture["payload_hash"]:
                return 409, {"detail": "capture_id já usado com conteúdo diferente"}
            return 200, {"capture_id": capture["capture_id"], "status": "stored", "duplicate": True}
        db.execute("""INSERT INTO stream_captures (
          capture_id, payload_hash, platform, path, request_id, status_code, content_type, capture_status,
          response_text, bytes, chunks, frames, done_markers, protocol_done, reader_done, truncated,
          stream_elapsed_ms, event_types_json, event_shapes_json, event_sequence_json, observed_at, received_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (capture["capture_id"], capture["payload_hash"], capture["platform"], capture["path"], capture["request_id"],
             capture["status_code"], capture["content_type"], capture["capture_status"], capture["response_text"], capture["bytes"], capture["chunks"],
             capture["frames"], capture["done_markers"], int(capture["protocol_done"]), int(capture["reader_done"]), int(capture["truncated"]),
             capture["stream_elapsed_ms"], json.dumps(capture["event_types"]), json.dumps(capture["event_shapes"]),
             json.dumps(capture["event_sequence"]), capture["observed_at"], received))
    return 201, {"capture_id": capture["capture_id"], "status": "stored", "duplicate": False}


class Handler(BaseHTTPRequestHandler):
    server_version = "StreamCapturePOC/0.1"

    def respond(self, code: int, value: dict) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self) -> bool:
        return token_matches(self.headers.get("Authorization", ""))

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/health":
            self.respond(200, {"status": "ok", "sqlite": True, "schema_version": "stream-capture-0.1"})
            return
        if route != "/v1/stream-captures/recent" or not self.authorized():
            self.respond(401 if route == "/v1/stream-captures/recent" else 404, {"detail": "Não autorizado ou rota inexistente"})
            return
        with connect() as db:
            rows = db.execute("SELECT capture_id, status_code, content_type, capture_status, response_text, bytes, chunks, frames, done_markers, protocol_done, reader_done, truncated, observed_at, received_at FROM stream_captures ORDER BY received_at DESC LIMIT 20").fetchall()
        self.respond(200, {"items": [dict(row) for row in rows]})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/v1/stream-captures":
            self.respond(404, {"detail": "Rota inexistente"})
            return
        if not self.authorized():
            self.respond(401, {"detail": "Token de laboratório inválido"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_BODY:
                raise ValueError("Tamanho de requisição inválido")
            capture = validate(json.loads(self.rfile.read(size)))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as error:
            self.respond(422, {"detail": str(error)[:200]})
            return
        code, result = store_capture(capture)
        self.respond(code, result)

    def log_message(self, _format: str, *_args: object) -> None:
        return  # Não registrar corpo, token, IP nem URL.


def main() -> None:
    if HOST not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("APP_HOST deve permanecer em loopback nesta POC.")
    if len(TOKEN) < 24:
        raise SystemExit("LAB_API_TOKEN precisa ter pelo menos 24 caracteres; configure backend/.env.")
    with connect() as db:
        db.commit()
    print(f"POC local pronta em http://{HOST}:{PORT} (SQLite: {DB_PATH.name})")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
