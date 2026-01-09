
# Ansible AutoProvisioner - Configuration Guide

## Configuration Overview

The system uses a hierarchical configuration system with the following precedence (highest to lowest):
1. Command-line arguments
2. Environment variables (planned)
3. Configuration file (`config.yaml`)
4. Default values

## Configuration Files

### 1. Main Configuration (`config.yaml`)

```yaml
# Daemon Configuration (optional)
daemon:
  interval: 30           # Polling interval in seconds
  state_file: "state.json"  # State persistence file
  log_dir: "logs"        # Log directory
  max_retries: 3         # Maximum playbook retry attempts
  static_inventory: "inventory.ini"  # Ansible inventory file
  detectors: ["static"]  # Enabled detectors

# Provisioning Rules
rules:
  # Rule 1: Match by host group
  - name: "provision-web-servers"
    match:
      groups: ["webservers", "nginx"]
    playbook: "playbooks/webserver.yml"
  
  # Rule 2: Match by host variable
  - name: "provision-production-servers"
    match:
      vars:
        environment: "production"
        role: "application"
    playbook: "playbooks/production-app.yml"
  
  # Rule 3: Match by both groups and variables
  - name: "provision-database-backup"
    match:
      groups: ["databases"]
      vars:
        backup_enabled: "true"
    playbook: "playbooks/database-backup.yml"
  
  # Rule 4: Multiple group matching (OR logic)
  - name: "provision-monitoring"
    match:
      groups: ["monitoring", "logging", "metrics"]
    playbook: "playbooks/monitoring-agent.yml"
```

### 2. Ansible Inventory (`inventory.ini`)

```ini
# Example inventory with groups and variables
[webservers]
web01.example.com ansible_host=192.168.1.10 environment=production role=nginx
web02.example.com ansible_host=192.168.1.11 environment=staging role=apache

[databases]
db01.example.com ansible_host=192.168.1.20 environment=production 
db02.example.com ansible_host=192.168.1.21 environment=staging backup_enabled=true

[production:children]
webservers
databases

[nginx]
web01.example.com

[apache]
web02.example.com

# Variables for all hosts in group
[webservers:vars]
http_port=80
max_clients=200

# Global variables
[all:vars]
ansible_user=admin
ansible_ssh_private_key_file=~/.ssh/id_rsa
```

## Rule Configuration Details

### Rule Structure

```yaml
- name: "unique-rule-name"           # Required: Descriptive name
  match:                             # Required: Matching conditions
    groups: ["group1", "group2"]     # Optional: List of groups to match
    vars:                            # Optional: Variables to match
      key1: "value1"
      key2: "value2"
  playbook: "path/to/playbook.yml"   # Required: Playbook to execute
```

### Matching Logic

1. **Group Matching**:
   - Uses OR logic within the `groups` list
   - Instance must belong to at least one specified group
   - Groups are case-sensitive

2. **Variable Matching**:
   - Uses AND logic for all specified variables
   - All variable conditions must be satisfied
   - Variable values are compared as strings
   - Supports nested variables via dot notation (e.g., `metadata.environment`)

3. **Combined Matching**:
   - Both `groups` and `vars` conditions must be satisfied
   - Empty `match` object matches all instances (use with caution)

## Command-Line Arguments

```bash
# Basic usage
python -m ansible_autoprovisioner.main --config config.yaml

# Full options
python -m ansible_autoprovisioner.main \
  --config config.yaml \           # Rules configuration file (required)
  --inventory inventory.ini \      # Ansible inventory file
  --state-file state.json \        # State persistence file
  --log-dir logs \                 # Log directory
  --interval 60 \                  # Polling interval (seconds)
  --max-retries 3 \                # Maximum playbook retries
  --verbose \                      # Enable debug logging
  --dry-run                        # Validate configuration without execution

# Daemon mode
python -m ansible_autoprovisioner.daemon --config config.yaml --interval 30
```

### Argument Reference

| Argument | Description | Default | Required |
|----------|-------------|---------|----------|
| `--config` | Path to rules YAML file | None | Yes |
| `--inventory` | Ansible inventory file | `inventory.ini` | No |
| `--state-file` | State persistence file | `state.json` | No |
| `--log-dir` | Directory for execution logs | `logs` | No |
| `--interval` | Polling interval in seconds | 60 | No |
| `--max-retries` | Maximum playbook retries | 3 | No |
| `--verbose` | Enable debug logging | False | No |
| `--dry-run` | Validate config without execution | False | No |

## State File Format

The state file (`state.json`) is automatically generated and managed:

```json
{
  "static-192.168.1.10": {
    "instance_id": "static-192.168.1.10",
    "ip_address": "192.168.1.10",
    "groups": ["webservers", "production"],
    "tags": {"environment": "production", "role": "nginx"},
    "detected_at": "2024-01-15 10:30:00",
    "last_seen_at": "2024-01-15 11:30:00",
    "updated_at": "2024-01-15 11:30:00",
    "playbooks": ["playbooks/webserver.yml"],
    "playbook_results": {
      "webserver": {
        "name": "webserver",
        "file": "playbooks/webserver.yml",
        "status": "success",
        "started_at": "2024-01-15 10:31:00",
        "completed_at": "2024-01-15 10:33:00",
        "duration_sec": 120.5,
        "retry_count": 0,
        "error": null
      }
    },
    "overall_status": "provisioned",
    "current_playbook": null,
    "last_attempt_at": "2024-01-15 10:31:00"
  }
}
```

## Logging Configuration

### Log Files Structure
```
logs/
├── static-192.168.1.10/
│   ├── webserver.log    # Playbook execution log
│   └── database.log     # Another playbook log
├── static-192.168.1.11/
│   └── webserver.log
└── daemon.log           # Daemon process log (if enabled)
```

### Log Levels
- `DEBUG`: Detailed information for troubleshooting
- `INFO`: General operational information
- `WARNING`: Warning messages (non-critical issues)
- `ERROR`: Error messages (failed operations)

## Validation Rules

The configuration system validates:

1. **File Existence**:
   - Rules configuration file must exist
   - Inventory file must exist (or be creatable)
   - Playbook files must exist (warning if not found)

2. **Directory Permissions**:
   - Log directory must be writable
   - State file directory must be writable

3. **Rule Validation**:
   - Rule names must be unique
   - Playbook paths must be valid
   - Match conditions must be properly formatted

## Environment Variables (Planned)

```bash
# Planned environment variable support
export ANSIBLE_AUTOPROV_INVENTORY="inventory.ini"
export ANSIBLE_AUTOPROV_STATE_FILE="state.json"
export ANSIBLE_AUTOPROV_LOG_DIR="/var/log/autoprovisioner"
export ANSIBLE_AUTOPROV_INTERVAL="30"
```

## Security Considerations

1. **File Permissions**:
   - Restrict read access to configuration files with secrets
   - Use appropriate permissions for state and log directories

2. **Inventory Security**:
   - Secure inventory files containing connection details
   - Use SSH keys instead of passwords
   - Consider using Ansible Vault for sensitive variables

3. **Playbook Safety**:
   - Validate playbooks before execution
   - Use `--check` mode for testing
   - Implement playbook signing/verification

4. **State File Protection**:
   - The state file contains instance metadata
   - Protect it from unauthorized modification
   - Regular backups recommended