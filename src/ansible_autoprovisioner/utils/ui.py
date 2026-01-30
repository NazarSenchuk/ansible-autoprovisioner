import json
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import unquote, parse_qs, urlparse
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
class UIRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/":
            return self.serve_dashboard()
        if path.endswith(".css"):
            return self.serve_template_asset(path)
        if path == "/health":
            return self.send_health()
        if path == "/api/config":
            return self.serve_config_json()
        if path == "/api/stats":
            return self.serve_stats_json()
        if path == "/api/instances":
            return self.serve_instances_json(parsed.query)
        if path.startswith("/api/instance/"):
            parts = path.split("/")
            if len(parts) < 4:
                return self.send_error(400, "Bad instance path")
            instance_id = parts[3]
            if len(parts) == 4:
                return self.serve_instance_details(instance_id)
            if len(parts) >= 5 and parts[4] == "logs":
                if len(parts) == 5:
                    return self.serve_instance_logs(instance_id, playbook=None)
                if len(parts) == 6:
                    return self.serve_instance_logs(instance_id, playbook=unquote(parts[5]))
            return self.send_error(404)
        return self.send_error(404)
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/instances":
            data = self._read_json()
            return self.handle_add_instance(data)
        if path.startswith("/api/instance/"):
            parts = path.split("/")
            if len(parts) < 5:
                return self.send_error(404)
            instance_id = parts[3]
            action = parts[4]
            if action == "retry":
                return self.handle_retry(instance_id)
            if action == "delete":
                return self.handle_delete(instance_id, parsed.query)
            return self.send_error(404)
        return self.send_error(404)
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/instance/"):
            parts = path.split("/")
            if len(parts) < 4:
                return self.send_error(400, "Bad instance path")
            instance_id = parts[3]
            return self.handle_delete(instance_id, parsed.query)
        return self.send_error(404)
    def _read_json(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))
    @property
    def mgmt(self):
        return self.server.management
    def handle_add_instance(self, data: Dict[str, Any]):
        result = self.mgmt.add_instance(
            instance_id=data.get("instance_id"),
            ip_address=data.get("ip_address"),
            groups=data.get("groups", []),
            tags=data.get("tags", {}),
            playbooks=data.get("playbooks", []),
        )
        self.send_json(result, status=200 if result.get("success") else 400)
    def handle_retry(self, instance_id: str):
        result = self.mgmt.retry_instance(instance_id)
        self.send_json(result, status=200 if result.get("success") else 400)
    def handle_delete(self, instance_id: str, query: str):
        params = parse_qs(query or "")
        force = params.get("force", ["false"])[0].lower() == "true"
        result = self.mgmt.delete_instance(instance_id, force=force)
        self.send_json(result, status=200 if result.get("success") else 400)
    def serve_instance_details(self, instance_id: str):
        result = self.mgmt.get_instance_details(instance_id)
        self.send_json(result, status=200 if result.get("success") else 404)
    def serve_instances_json(self, query: str):
        params = parse_qs(query or "")
        status_filter = params.get("status", [None])[0]
        instances = self.mgmt.list_instances(status_filter)
        self.send_json([i.to_dict() for i in instances])
    def serve_stats_json(self):
        stats = self.mgmt.get_stats()
        self.send_json(stats)
    def serve_config_json(self):
        cfg = self.mgmt.get_config()
        self.send_json(cfg)
    def serve_instance_logs(self, instance_id: str, playbook: Optional[str]):
        result = self.mgmt.get_logs(instance_id=instance_id, playbook=playbook)
        if not result.get("success"):
            return self.send_error(404, result.get("error", "Not found"))
        if playbook is None:
            return self.send_json(result)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(result.get("content", "").encode("utf-8", errors="ignore"))
    def serve_dashboard(self):
        html = self.load_template("dashboard.html")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    def serve_template_asset(self, path: str):
        filename = path.lstrip("/")
        file_path = TEMPLATES_DIR / filename
        if not file_path.exists():
            return self.send_error(404)
        content_type = "text/plain"
        if file_path.suffix == ".css":
            content_type = "text/css"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(file_path.read_bytes())
    def send_health(self):
        self.send_json({"status": "ok", "timestamp": datetime.utcnow().isoformat()})
    def send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
    def load_template(self, name: str) -> str:
        path = TEMPLATES_DIR / name
        if not path.exists():
            return "<h1>Template not found</h1>"
        return path.read_text(encoding="utf-8")
    def log_message(self, fmt, *args):
        logger.debug(fmt % args)
class UIServer:
    def __init__(self, management, host: str = "0.0.0.0", port: int = 8080):
        self.server = HTTPServer((host, port), UIRequestHandler)
        self.server.management = management
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
    def start(self):
        self.thread.start()
        logger.info("UI started")
        return True
    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        logger.info("UI stopped")
        return False
