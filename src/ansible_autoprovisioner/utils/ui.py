import json
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any
from urllib.parse import unquote
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
LOGS_DIR = Path("logs")

class UIRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/":
            self.serve_dashboard()
        elif self.path.endswith(".css"):
            self.serve_template_asset()
        elif self.path == "/api/instances":
            self.serve_instances_json()
        elif self.path == "/api/stats":
            self.serve_stats_json()
        elif self.path == "/api/config":
            self.serve_config_json()
        elif self.path == "/health":
            self.send_health()
        elif self.path.startswith("/api/instance/") and "/logs" in self.path:
            self.serve_instance_logs()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith("/api/instance/") and self.path.endswith("/retry"):
            instance_id = self.path.split("/")[3]
            self.handle_retry(instance_id)
            return
        self.send_error(404)

    def serve_dashboard(self):
        html = self.load_template("dashboard.html")
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def serve_template_asset(self):
        filename = self.path.lstrip("/")
        file_path = TEMPLATES_DIR / filename

        if not file_path.exists():
            self.send_error(404)
            return

        content_type = "text/plain"
        if file_path.suffix == ".css":
            content_type = "text/css"

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(file_path.read_bytes())

    def serve_instances_json(self):
        state = self.server.daemon_ref.state

        data = []
        for inst in state.get_instances():
            data.append({
                "instance_id": inst.instance_id,
                "ip_address": inst.ip_address,
                "groups": inst.groups,
                "overall_status": inst.overall_status.value,
                "updated_at": inst.updated_at,
                "playbooks": inst.playbooks,
                "playbook_results": {
                    k: {
                        "status": v.status.value,
                        "retry_count": v.retry_count,
                        "error": v.error,
                    }
                    for k, v in inst.playbook_results.items()
                }
            })

        self.send_json(data)

    def serve_stats_json(self):
        instances = self.server.daemon_ref.state.get_instances()

        self.send_json({
            "instances": len(instances),
            "successful": sum(1 for i in instances if i.overall_status.value == "provisioned"),
            "failed": sum(1 for i in instances if i.overall_status.value == "failed"),
            "interval": self.server.daemon_ref.config.interval,
        })

    def serve_config_json(self):
        cfg = self.server.daemon_ref.config

        self.send_json({
            "rules_count": len(cfg.rules),
            "state_file": cfg.state_file,
            "inventory": cfg.static_inventory,
            "interval": cfg.interval,
            "max_retries": cfg.max_retries,
        })

    def serve_instance_logs(self):
        parts = self.path.split("/")

        try:
            instance_id = parts[3]
        except IndexError:
            self.send_error(400)
            return

        instance_log_dir = LOGS_DIR / instance_id

        if not instance_log_dir.exists():
            self.send_error(404, "No logs for instance")
            return

        if len(parts) == 5:
            logs = [
                f.name
                for f in instance_log_dir.iterdir()
                if f.is_file() and f.suffix == ".log"
            ]
            self.send_json({"instance": instance_id, "logs": logs})
            return

        playbook = unquote(parts[5])
        log_file = instance_log_dir / playbook

        if not log_file.exists():
            self.send_error(404, "Log not found")
            return

        content = log_file.read_text(errors="ignore")

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(content.encode())



    def handle_retry(self, instance_id: str):
        daemon = self.server.daemon_ref
        state = daemon.state

        for inst in state.get_instances():
            if inst.instance_id == instance_id and inst.overall_status.value in ("failed", "partial_failure"):
                state.mark_final_status(inst.instance_id, inst.overall_status.__class__("new"))
                self.send_json({"success": True})
                return

        self.send_json({"success": False}, status=400)

    def send_health(self):
        self.send_json({
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat()
        })

    def send_json(self, data: Dict[str, Any], status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def load_template(self, name: str) -> str:
        path = TEMPLATES_DIR / name
        if not path.exists():
            return "<h1>Template not found</h1>"
        return path.read_text(encoding="utf-8")

    def log_message(self, fmt, *args):
        logger.debug(fmt % args)


class UIServer:

    def __init__(self, daemon_ref, host="0.0.0.0", port=8080):
        self.daemon_ref = daemon_ref
        self.server = HTTPServer((host, port), UIRequestHandler)
        self.server.daemon_ref = daemon_ref
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )

    def start(self):
        self.thread.start()
        logger.info("UI started")

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
