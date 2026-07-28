from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"

sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.agent.agent_v2 import ReActAgentV2
from src.chatbot import BaselineChatbot
from src.core.groq_provider import GroqProvider
from src.core.ollama_provider import OllamaProvider
from src.tools import TOOL_REGISTRY


DEFAULT_PROVIDER = "groq"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OLLAMA_MODEL = "qwen3.5:4b"


class LiveDemoHandler(BaseHTTPRequestHandler):
    server_version = "LiveAgentDemo/1.0"

    def do_GET(self) -> None:
        if self.path == "/api/health":
            provider = self._make_provider(DEFAULT_PROVIDER, "")
            self._send_json({"ok": True, "provider": provider.__class__.__name__, "model": provider.model_name})
            return

        path = "/" if self.path == "/" else unquote(self.path.split("?", 1)[0])
        file_path = WEB_ROOT / "index.html" if path == "/" else WEB_ROOT / path.lstrip("/")
        resolved = file_path.resolve()
        if WEB_ROOT.resolve() not in resolved.parents and resolved != WEB_ROOT.resolve():
            self.send_error(403)
            return
        if not resolved.exists() or not resolved.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        body = resolved.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path == "/api/chat/stream":
            self._handle_chat_stream()
            return

        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            query = str(payload.get("query", "")).strip()
            mode = str(payload.get("mode", "agent")).strip().lower()
            provider_name = str(payload.get("provider", DEFAULT_PROVIDER)).strip().lower()
            model = str(payload.get("model", "")).strip()
            if not query:
                self._send_json({"ok": False, "error": "missing_query"}, status=400)
                return

            provider = self._make_provider(provider_name, model)
            if mode == "baseline":
                result = BaselineChatbot(provider).chat(query)
            else:
                result = ReActAgentV2(provider, TOOL_REGISTRY, max_steps=8).run(query)

            self._send_json(
                {
                    "ok": True,
                    "mode": mode,
                    "provider": provider_name,
                    "model": provider.model_name,
                    "query": query,
                    "result": result,
                }
            )
        except Exception as exc:
            self._send_json({"ok": False, "error": type(exc).__name__, "message": str(exc)}, status=500)

    def _handle_chat_stream(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            query = str(payload.get("query", "")).strip()
            mode = str(payload.get("mode", "agent")).strip().lower()
            provider_name = str(payload.get("provider", DEFAULT_PROVIDER)).strip().lower()
            model = str(payload.get("model", "")).strip()
            if not query:
                self._send_stream_error("missing_query", "query is required", status=400)
                return

            provider = self._make_provider(provider_name, model)
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self._write_event(
                {
                    "type": "start",
                    "mode": mode,
                    "provider": provider_name,
                    "model": provider.model_name,
                    "query": query,
                }
            )

            if mode == "baseline":
                result = BaselineChatbot(provider).chat(query)
                self._write_event({"type": "result", "result": result})
            else:
                agent = ReActAgentV2(provider, TOOL_REGISTRY, max_steps=8)
                agent.run(query, on_event=self._write_event)
        except Exception as exc:
            try:
                self._write_event({"type": "error", "error": type(exc).__name__, "message": str(exc)})
            except Exception:
                pass

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_stream_error(self, error: str, message: str, status: int = 500) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.end_headers()
        self._write_event({"type": "error", "error": error, "message": message})

    def _write_event(self, payload: dict) -> None:
        self.wfile.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        self.wfile.flush()

    def _make_provider(self, provider_name: str, model: str):
        if provider_name == "ollama":
            return OllamaProvider(model_name=model or DEFAULT_OLLAMA_MODEL)
        return GroqProvider(model_name=model or DEFAULT_GROQ_MODEL)


def main() -> None:
    host = "127.0.0.1"
    port = int(os.getenv("PORT", "8001"))
    server = ThreadingHTTPServer((host, port), LiveDemoHandler)
    print(f"Live demo server: http://{host}:{port}")
    print(f"Provider mặc định: {DEFAULT_PROVIDER}")
    server.serve_forever()


if __name__ == "__main__":
    main()
