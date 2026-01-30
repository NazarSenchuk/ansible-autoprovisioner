# Ansible AutoProvisioner

An intelligent automation system that dynamically detects infrastructure changes and automatically executes appropriate Ansible playbooks based on predefined rules.

## 🎯 What Problem Does This Solve?

Tired of manually running Ansible playbooks when new servers spin up?  
This tool automatically:
- 🔍 **Detects** new infrastructure instances (Static Inventory or AWS)
- 🎯 **Matches** them against your business rules
- ⚡ **Executes** appropriate Ansible playbooks immediately
- 📊 **Tracks** everything automatically with a robust state model

**Think of it as "GitHub Actions for your infrastructure"** - but triggered by infrastructure changes instead of code commits.

## ✨ Features

- **Automatic Instance Detection**: Discovers instances from Ansible inventory files or cloud platforms (AWS).
- **Rule-Based Provisioning**: Highly flexible rule engine to match instances to playbooks based on host groups, tags, or metadata.
- **5-Status State Model**: Clean lifecycle management using `PENDING`, `RUNNING`, `SUCCESS`, `ERROR`, and `ORPHANED`.
- **Prioritized Execution**: Guaranteed delivery for new instances (`PENDING`) before retrying failed ones (`ERROR`).
- **Slack & Telegram Notifications**: Real-time alerts for provisioning success or failure.
- **Web Dashboard**: Modern UI for monitoring activities, viewing logs, and managing retries.
- **Concurrent Execution**: Provisions multiple instances simultaneously using thread pools for high throughput.
- **Comprehensive Logging**: Detailed execution logs per instance and per playbook for easy troubleshooting.

![Ansible AutoProvisioner UI](./docs/ui.png)

## 🚀 Quick Start

### Installation

```bash
pip install ansible-autoprovisioner
```

### Basic Configuration

1. **Create your rules configuration** (`rules.yml`):
```yaml
daemon:
  interval: 30
  max_retries: 3
  ui: true

detectors:
  static:
    inventory: "./inventory.ini"

rules:
  - name: "setup-web"
    playbook: "./playbooks/nginx.yml"

groups:
  web-servers:
    match:
      role: "webserver"
    rules:
      - "setup-web"

notifications:
  slack:
    webhook_url: "https://hooks.slack.com/services/..."
```

2. **Run the provisioner**:
```bash
ansible-autoprovisioner --config rules.yml --ui
```

## 📁 Project Structure

```
ansible_autoprovisioner/
├── detectors/          # Infrastructure discovery system (AWS, Static)
├── notifications/      # Notification handlers (Slack, Telegram)
├── matcher.py         # Rule matching engine
├── executor.py        # Ansible playbook execution engine
├── state.py           # State management and persistence
├── daemon.py          # Continuous monitoring loop
├── config.py          # Configuration and validation
├── main.py            # CLI entry point
└── utils/             # UI Server, API, and Logging utilities
```

## ⚙️ How it Works

1. **Detection**: Periodically scans your infrastructure (e.g., AWS tags or inventory files).
2. **Matching**: Compares detected instances against your defined `groups` and `rules`.
3. **Execution**: If an instance needs provisioning, it's marked `PENDING` and queued for a thread-pooled Ansible run.
4. **Tracking**: The `state.json` file records every step, ensuring playbooks aren't re-run unnecessarily.
5. **Alerting**: Once finished, the system notifies you via your chosen channels (Slack/Telegram).

## 🗺️ Roadmap

### 🚀 Upcoming Features
- **Cloud Platform Detectors**: Expanding beyond AWS to Azure and GCP.
- **Advanced Matching**: Regex support and complex logic (AND/OR/NOT).
- **Dependency Tracking**: Playbook dependencies and execution ordering.
- **Enhanced UI**: Visual rule builder and real-time metrics charts.
- **Infrastructure Integrations**: Terraform post-provision hooks and monitoring integration (Prometheus/Datadog).

## 📁 Documentation

Detailed documentation is available in the `docs/` directory:
- [Architecture Documentation](docs/architecture.md) - Technical system design
- [Configuration Guide](docs/configuration.md) - Complete reference for all YAML options
- [Usage Examples](docs/examples.md) - Complex patterns and production setups

## ⚖️ License

MIT License.
