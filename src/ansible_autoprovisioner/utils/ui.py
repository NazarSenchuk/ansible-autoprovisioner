
import json
import logging
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class UIRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for the web UI"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.serve_dashboard()
        elif self.path == '/api/instances':
            self.serve_instances_json()
        elif self.path == '/api/stats':
            self.serve_stats_json()
        elif self.path == '/api/config':
            self.serve_config_json()
        elif self.path == '/health':
            self.send_health()
        elif self.path.startswith('/static/'):
            self.serve_static()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests for actions"""
        if self.path.startswith('/api/instance/'):
            parts = self.path.split('/')
            if len(parts) >= 5:
                instance_id = parts[3]
                action = parts[4]
                self.handle_instance_action(instance_id, action)
                return
        self.send_error(404, "Not Found")
    
    def serve_dashboard(self):
        """Serve the main dashboard HTML page"""
        html_content = self.load_template('dashboard.html')
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def serve_instances_json(self):
        """Serve instances data as JSON"""
        daemon = self.server.daemon_ref
        instances = daemon.state.get_instances()
        
        # Convert instances to serializable format
        instances_data = []
        for inst in instances:
            instances_data.append({
                'instance_id': inst.instance_id,
                'ip_address': inst.ip_address,
                'groups': inst.groups,
                'tags': inst.tags,
                'detected_at': inst.detected_at.isoformat() if inst.detected_at else None,
                'last_seen_at': inst.last_seen_at.isoformat() if inst.last_seen_at else None,
                'updated_at': inst.updated_at.isoformat() if inst.updated_at else None,
                'playbooks': inst.playbooks,
                'playbook_results': [
                    {
                        'name': name,
                        'status': result.status.value,
                        'started_at': result.started_at.isoformat() if result.started_at else None,
                        'duration_sec': result.duration_sec,
                        'retry_count': result.retry_count,
                        'error': result.error
                    }
                    for name, result in inst.playbook_results.items()
                ],
                'overall_status': inst.overall_status.value,
                'current_playbook': inst.current_playbook,
            })
        
        self.send_json(instances_data)
    
    def serve_stats_json(self):
        """Serve statistics data as JSON"""
        daemon = self.server.daemon_ref
        
        # Calculate uptime
        uptime = datetime.now() - daemon.stats['start_time']
        
        stats_data = {
            **daemon.stats,
            'start_time': daemon.stats['start_time'].isoformat(),
            'uptime_seconds': uptime.total_seconds(),
            'uptime_human': str(uptime).split('.')[0],  # Remove microseconds
            'interval': daemon.config.interval,
            'max_retries': daemon.config.max_retries,
        }
        
        self.send_json(stats_data)
    
    def serve_config_json(self):
        """Serve configuration data as JSON"""
        daemon = self.server.daemon_ref
        config = daemon.config
        
        config_data = {
            'state_file': str(config.state_file),
            'log_dir': str(config.log_dir),
            'static_inventory': str(config.static_inventory),
            'interval': config.interval,
            'max_retries': config.max_retries,
            'rules_count': len(config.rules),
            'detectors': [str(d) for d in daemon.detectors.detectors],
        }
        
        self.send_json(config_data)
    
    def handle_instance_action(self, instance_id: str, action: str):
        """Handle actions on instances (retry, etc.)"""
        daemon = self.server.daemon_ref
        
        if action == 'retry':
            # Find instance and mark for retry
            instances = daemon.state.get_instances()
            for inst in instances:
                if inst.instance_id == instance_id:
                    if inst.overall_status.value in ['failed', 'partial_failure']:
                        # Reset status to NEW to trigger reprovisioning
                        daemon.state.mark_final_status(
                            instance_id, 
                            daemon.state._instances[instance_id].overall_status.__class__('new')
                        )
                        logger.info(f"UI: Manually triggered retry for {instance_id}")
                        self.send_json({'success': True, 'message': f'Retry triggered for {instance_id}'})
                        return
        
        self.send_json({'success': False, 'error': 'Invalid action or instance state'}, status=400)
    
    def serve_static(self):
        """Serve static files (CSS, JS, etc.)"""
        # For now, we'll serve a simple CSS file
        if self.path == '/static/style.css':
            css = """
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 10px; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 25px; }
            .stat-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .stat-card h3 { margin-top: 0; color: #2c3e50; }
            .stat-value { font-size: 24px; font-weight: bold; color: #3498db; }
            .table-container { background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 25px; }
            table { width: 100%; border-collapse: collapse; }
            th { background: #2c3e50; color: white; padding: 15px; text-align: left; }
            td { padding: 12px 15px; border-bottom: 1px solid #eee; }
            tr:hover { background: #f8f9fa; }
            .status-badge { padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }
            .status-new { background: #e3f2fd; color: #1976d2; }
            .status-provisioning { background: #fff3e0; color: #f57c00; }
            .status-provisioned { background: #e8f5e9; color: #388e3c; }
            .status-failed { background: #ffebee; color: #d32f2f; }
            .status-partial { background: #fff8e1; color: #ffa000; }
            .status-orphaned { background: #f5f5f5; color: #616161; }
            .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: 600; }
            .btn-primary { background: #3498db; color: white; }
            .btn-primary:hover { background: #2980b9; }
            .last-updated { text-align: center; color: #7f8c8d; font-size: 12px; margin-top: 20px; }
            """
            self.send_response(200)
            self.send_header('Content-type', 'text/css')
            self.end_headers()
            self.wfile.write(css.encode())
        else:
            self.send_error(404)
    
    def send_health(self):
        """Health check endpoint"""
        self.send_json({
            'status': 'healthy', 
            'timestamp': datetime.now().isoformat(),
            'service': 'ansible-autoprovisioner-ui'
        })
    
    def send_json(self, data: Dict[str, Any], status: int = 200):
        """Helper to send JSON response"""
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())
    
    def load_template(self, template_name: str) -> str:
        """Load HTML template"""
        # Simple inline template for now
        if template_name == 'dashboard.html':
            return self.get_dashboard_template()
        return f"<h1>Template {template_name} not found</h1>"
    
    def get_dashboard_template(self) -> str:
        """Return the dashboard HTML template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Ansible AutoProvisioner</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="stylesheet" href="/static/style.css">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1><i class="fas fa-robot"></i> Ansible AutoProvisioner</h1>
                    <p>Automated infrastructure provisioning daemon with real-time monitoring</p>
                </div>
                
                <div class="stats-grid" id="stats-container">
                    <div class="stat-card">
                        <h3><i class="fas fa-sync-alt"></i> Cycles</h3>
                        <div class="stat-value" id="stat-cycles">0</div>
                    </div>
                    <div class="stat-card">
                        <h3><i class="fas fa-server"></i> Instances</h3>
                        <div class="stat-value" id="stat-instances">0</div>
                    </div>
                    <div class="stat-card">
                        <h3><i class="fas fa-check-circle"></i> Successful</h3>
                        <div class="stat-value" id="stat-successful">0</div>
                    </div>
                    <div class="stat-card">
                        <h3><i class="fas fa-times-circle"></i> Failed</h3>
                        <div class="stat-value" id="stat-failed">0</div>
                    </div>
                </div>
                
                <div class="stats-grid">
                    <div class="stat-card">
                        <h3><i class="fas fa-info-circle"></i> Daemon Info</h3>
                        <div id="daemon-info">Loading...</div>
                    </div>
                    <div class="stat-card">
                        <h3><i class="fas fa-cogs"></i> Configuration</h3>
                        <div id="config-info">Loading...</div>
                    </div>
                </div>
                
                <div class="table-container">
                    <h3 style="padding: 20px 20px 0; margin: 0;"><i class="fas fa-list"></i> Managed Instances</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Instance ID</th>
                                <th>IP Address</th>
                                <th>Status</th>
                                <th>Groups</th>
                                <th>Playbooks</th>
                                <th>Last Updated</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="instances-body">
                            <tr><td colspan="7" style="text-align: center; padding: 30px;">Loading instances...</td></tr>
                        </tbody>
                    </table>
                </div>
                
                <div class="last-updated" id="last-updated">
                    Last updated: <span id="update-time">Never</span> | 
                    Auto-refresh: <input type="checkbox" id="auto-refresh" checked> |
                    Refresh interval: <select id="refresh-interval">
                        <option value="5000">5 sec</option>
                        <option value="10000" selected>10 sec</option>
                        <option value="30000">30 sec</option>
                        <option value="60000">1 min</option>
                    </select>
                    <button onclick="manualRefresh()" class="btn btn-primary" style="margin-left: 10px;">
                        <i class="fas fa-redo"></i> Refresh Now
                    </button>
                </div>
            </div>
            
            <script>
                let refreshInterval = 10000;
                let refreshTimer = null;
                
                async function fetchData() {
                    try {
                        const [instancesRes, statsRes, configRes] = await Promise.all([
                            fetch('/api/instances'),
                            fetch('/api/stats'),
                            fetch('/api/config')
                        ]);
                        
                        const instances = await instancesRes.json();
                        const stats = await statsRes.json();
                        const config = await configRes.json();
                        
                        updateUI(instances, stats, config);
                        
                        document.getElementById('update-time').textContent = new Date().toLocaleTimeString();
                    } catch (error) {
                        console.error('Failed to fetch data:', error);
                        document.getElementById('instances-body').innerHTML = 
                            '<tr><td colspan="7" style="text-align: center; padding: 30px; color: #d32f2f;">' +
                            '<i class="fas fa-exclamation-triangle"></i> Error loading data</td></tr>';
                    }
                }
                
                function updateUI(instances, stats, config) {
                    // Update stats
                    document.getElementById('stat-cycles').textContent = stats.cycles || 0;
                    document.getElementById('stat-instances').textContent = stats.instances_processed || 0;
                    document.getElementById('stat-successful').textContent = stats.successful || 0;
                    document.getElementById('stat-failed').textContent = stats.failed || 0;
                    
                    // Update daemon info
                    document.getElementById('daemon-info').innerHTML = `
                        <div>Uptime: <strong>${stats.uptime_human || 'N/A'}</strong></div>
                        <div>Interval: <strong>${stats.interval || 30}s</strong></div>
                        <div>Retries: <strong>${stats.retried || 0}</strong></div>
                    `;
                    
                    // Update config info
                    document.getElementById('config-info').innerHTML = `
                        <div>Rules: <strong>${config.rules_count || 0}</strong></div>
                        <div>State file: <code>${config.state_file || 'N/A'}</code></div>
                        <div>Inventory: <code>${config.static_inventory || 'N/A'}</code></div>
                    `;
                    
                    // Update instances table
                    const tbody = document.getElementById('instances-body');
                    
                    if (instances.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 30px;">No instances detected yet</td></tr>';
                        return;
                    }
                    
                    tbody.innerHTML = instances.map(inst => {
                        const statusClass = `status-${inst.overall_status}`;
                        const lastUpdated = inst.updated_at ? new Date(inst.updated_at).toLocaleString() : 'N/A';
                        const playbookCount = inst.playbook_results ? inst.playbook_results.length : 0;
                        
                        let actions = '';
                        if (inst.overall_status === 'failed' || inst.overall_status === 'partial_failure') {
                            actions = `<button onclick="retryInstance('${inst.instance_id}')" class="btn btn-primary">
                                <i class="fas fa-redo"></i> Retry
                            </button>`;
                        }
                        
                        return `
                            <tr>
                                <td><strong><i class="fas fa-server"></i> ${inst.instance_id}</strong></td>
                                <td><code>${inst.ip_address || 'N/A'}</code></td>
                                <td><span class="status-badge ${statusClass}">${inst.overall_status.toUpperCase()}</span></td>
                                <td>${inst.groups ? inst.groups.join(', ') : '—'}</td>
                                <td>${playbookCount} playbook(s)</td>
                                <td>${lastUpdated}</td>
                                <td>${actions}</td>
                            </tr>
                        `;
                    }).join('');
                }
                
                function retryInstance(instanceId) {
                    fetch(`/api/instance/${instanceId}/retry`, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert(`Retry triggered for ${instanceId}`);
                                manualRefresh();
                            } else {
                                alert(`Error: ${data.error}`);
                            }
                        })
                        .catch(error => {
                            console.error('Retry failed:', error);
                            alert('Failed to trigger retry');
                        });
                }
                
                function manualRefresh() {
                    if (refreshTimer) clearTimeout(refreshTimer);
                    fetchData();
                    startRefreshTimer();
                }
                
                function startRefreshTimer() {
                    if (document.getElementById('auto-refresh').checked) {
                        refreshTimer = setTimeout(() => {
                            fetchData();
                            startRefreshTimer();
                        }, refreshInterval);
                    }
                }
                
                // Event listeners
                document.getElementById('auto-refresh').addEventListener('change', function() {
                    if (this.checked) {
                        startRefreshTimer();
                    } else {
                        if (refreshTimer) clearTimeout(refreshTimer);
                    }
                });
                
                document.getElementById('refresh-interval').addEventListener('change', function() {
                    refreshInterval = parseInt(this.value);
                    if (document.getElementById('auto-refresh').checked) {
                        if (refreshTimer) clearTimeout(refreshTimer);
                        startRefreshTimer();
                    }
                });
                
                // Initial load
                fetchData();
                startRefreshTimer();
            </script>
        </body>
        </html>
        """
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        logger.debug(f"HTTP {self.address_string()} - {format % args}")


class UIServer:
    """Manage the UI HTTP server"""
    
    def __init__(self, daemon_ref, host: str = '0.0.0.0', port: int = 8080):
        self.daemon_ref = daemon_ref
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        
    def start(self):
        """Start the UI server in a background thread"""
        try:
            # Create HTTP server
            server_address = (self.host, self.port)
            self.server = HTTPServer(server_address, UIRequestHandler)
            self.server.daemon_ref = self.daemon_ref
            
            # Start server in background thread
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            
            logger.info(f"✅ Web UI started at http://{self.host}:{self.port}")
            logger.info(f"   • Dashboard: http://{self.host}:{self.port}/")
            logger.info(f"   • API (instances): http://{self.host}:{self.port}/api/instances")
            logger.info(f"   • Health: http://{self.host}:{self.port}/health")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start UI server: {e}")
            return False
    
    def stop(self):
        """Stop the UI server"""
        if self.server:
            logger.info("Shutting down UI server...")
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            logger.info("UI server stopped")