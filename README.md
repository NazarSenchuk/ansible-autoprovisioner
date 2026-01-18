# Ansible AutoProvisioner

An intelligent automation system that dynamically detects infrastructure changes and automatically executes appropriate Ansible playbooks based on predefined rules.

## Features

- **Automatic Instance Detection**: Discovers instances from Ansible inventory files
- **Rule-Based Provisioning**: Executes playbooks based on host groups and variables
- **State Management**: Tracks provisioning status to prevent duplicate executions
- **Concurrent Execution**: Provisions multiple instances simultaneously using thread pools
- **Retry Logic**: Automatic retry of failed playbooks with configurable limits
- **Orphan Detection**: Identifies instances that are no longer present in inventory
- **Comprehensive Logging**: Detailed execution logs for troubleshooting

![UI](./ui.png)

~[UI](./ui.png)
## Quick Start

### Installation

  
# Install dependencies 
```bash 
pip install ansible-autoprovisioner
```
### Basic Configuration

1. **Create rules configuration** (`config.yaml`):
```yaml
rules:
  - name: "provision-web-servers"
    match:
      groups: ["webservers"]
    playbook: "playbooks/web-server.yml"
  
  - name: "provision-database-servers"
    match:
      groups: ["databases"]
    playbook: "playbooks/database.yml"
  
  - name: "provision-production"
    match:
      vars:
        environment: "production"
    playbook: "playbooks/production-setup.yml"
```

2. **Create Ansible inventory** (`inventory.ini`):
```ini
[webservers]
web01.example.com ansible_host=192.168.1.10 environment=production
web02.example.com ansible_host=192.168.1.11 environment=staging

[databases]
db01.example.com ansible_host=192.168.1.20
```

3. **Run the provisioner**:
```bash
ansible_autoprovisioner --config config.yaml --interval 60 --inventory inventory.ini 
```

## Configuration Files

- `config.yaml` - Rule definitions and daemon settings
- `inventory.ini` - Ansible inventory file (source for static detection)
- `state.json` - Persistent state tracking (auto-generated)
- `logs/` - Execution logs directory (auto-generated)

## Project Structure

```
ansible_autoprovisioner/
├── detectors/          # Instance detection system
│   ├── base.py        # Base detector interface
│   ├── static.py      # Static inventory detector
│   └── manager.py     # Detector coordination
├── matcher.py         # Rule matching engine
├── executor.py        # Ansible playbook execution
├── state.py           # State management and persistence
├── daemon.py          # Daemon service implementation
├── config.py          # Configuration loading and validation
├── main.py            # CLI entry point
├── utils/             # Utilities
│   ├── cli.py         # Command-line argument parsing
│   └── logging.py     # Logging configuration
└── notifier/          # Notification system (to be implemented)
```

## Requirements

- Python 3.8+
- Ansible 2.9+
- PyYAML

## Documentation

- [Architecture Documentation](ARCHITECTURE.md) - Detailed system design
- [Configuration Guide](CONFIGURATION.md) - Complete configuration reference
- [Examples](EXAMPLES.md) - Usage examples and patterns



## Roadmap & Future Features

### 🚀 Upcoming Features

#### 1. **Cloud Platform Detectors**
- **AWS EC2 Detector**: Automatic discovery of EC2 instances with tags
- **Azure VM Detector**: Azure Virtual Machines detection with metadata
- **GCP Compute Detector**: Google Cloud Platform instance discovery


#### 2. **Web UI & Dashboard**
- **Real-time Monitoring**: Live view of provisioning activities
- **Instance Inventory**: Visual dashboard of detected instances
- **Rule Management**: Web interface for creating and testing rules
- **Execution History**: Timeline of provisioning events
- **Performance Metrics**: Charts and graphs of system performance
- **User Management**: Role-based access control (RBAC)

#### 4. **Advanced Matching Engine**
- **Complex Logic**: AND/OR/NOT operations in matching rules
- **Regex Matching**: Regular expression support for hostnames and variables
- **Temporal Rules**: Time-based provisioning schedules
- **Dependency Tracking**: Playbook dependencies and ordering
- **Conditional Execution**: If-else logic in rule evaluation

#### 5. **Notification System**
- **Multiple Channels**: Slack, Email, Teams, Discord, Webhooks
- **Event-Based Notifications**: Configurable triggers for different events
- **Alert Templates**: Customizable notification templates
- **Notification Groups**: Group notifications by team or service
- **Escalation Policies**: Automated escalation for critical failures

#### 6. **Integration Ecosystem**
- **CI/CD Integration**: GitLab CI, GitHub Actions, Jenkins
- **Monitoring Integration**: Prometheus, Grafana, Datadog
- **ServiceNow Integration**: Automatic ticket creation
- **Terraform Integration**: Post-provision automation
- **API Gateway**: REST API for external integrations

#### 7. **Enhanced Execution Engine**
- **Dry-run Mode**: Simulated execution without changes
- **Rollback Support**: Automatic rollback on failure
- **Parallel Playbooks**: Multiple playbooks per instance concurrently
- **Rate Limiting**: Configurable rate limits for API calls
- **Health Checks**: Pre- and post-execution validation


