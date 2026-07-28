from __future__ import annotations

import json
import mimetypes
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
from src.core.ollama_provider import OllamaProvider
from src.tools import TOOL_REGISTRY


DEFAULT_MODEL = "qwen3.5:4b"


class LiveDemoHandler(BaseHTTPRequestHandler):
    server_version = "LiveAgentDemo/1.0"

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json({"ok": True, "model": DEFAULT_MODEL})
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
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            query = str(payload.get("query", "")).strip()
            mode = str(payload.get("mode", "agent")).strip().lower()
            model = str(payload.get("model", DEFAULT_MODEL)).strip() or DEFAULT_MODEL
            if not query:
                self._send_json({"ok": False, "error": "missing_query"}, status=400)
                return

            provider = OllamaProvider(model_name=model)
            if mode == "baseline":
                result = BaselineChatbot(provider).chat(query)
            else:
                result = ReActAgentV2(provider, TOOL_REGISTRY, max_steps=8).run(query)

            self._send_json({"ok": True, "mode": mode, "model": model, "query": query, "result": result})
        except Exception as exc:
            self._send_json({"ok": False, "error": type(exc).__name__, "message": str(exc)}, status=500)

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), LiveDemoHandler)
    print(f"Live demo server: http://{host}:{port}")
    print(f"Model mặc định: {DEFAULT_MODEL}")
    server.serve_forever()


if __name__ == "__main__":
    main()
