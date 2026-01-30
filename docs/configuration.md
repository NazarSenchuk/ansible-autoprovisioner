# Configuration Guide

Ansible AutoProvisioner is configured via a central YAML file (e.g., `rules.yml`). This guide details every configuration option available.

## 🚀 Global Settings (`daemon`)

Settings that control the behavior of the daemon process itself.

| Option | Description | Default |
| --- | --- | --- |
| `interval` | Seconds to wait between monitoring cycles. | `30` |
| `max_retries` | Max times to retry a failed instance before marking it `ERROR`. | `3` |
| `state_file` | Path to the persistent JSON state file. | `state.json` |
| `log_dir` | Directory where instance-specific logs will be stored. | `./logs` |
| `ui` | Enable the built-in monitoring dashboard. | `true` |
| `ui_host` | Host address to bind the UI server to. | `0.0.0.0` |
| `ui_port` | Port for the UI server. | `8080` |

## 🔍 Detectors (`detectors`)

Define the sources used to discover your infrastructure.

### Static Inventory
```yaml
detectors:
  static:
    inventory: "./inventory.ini"  # Path to Ansible inventory
```

### AWS EC2
```yaml
detectors:
  aws:
    region: "us-east-1"           # AWS Region
    profile: "default"           # AWS CLI Profile (optional)
```

## 🎯 Matching Logic (`groups` & `rules`)

The matching system links discovered instances to playbooks.

### Defining Rules
Rules define *what* to run.
```yaml
rules:
  - name: "install-nginx"
    playbook: "./playbooks/nginx.yml"
    vars:                         # Optional: Extra vars for this playbook
      http_port: 80
```

### Defining Groups
Groups define *where* to run playbooks.
```yaml
groups:
  web-servers:
    match:                        # Logic to select instances
      role: "web"                 # Match by tag or host variable
      env: "prod"
    rules:
      - "install-nginx"           # Rule name to apply
```

## 📢 Notifications (`notifications`)

Configure where alerts are sent when provisioning finishes.

### Slack
```yaml
notifications:
  slack:
    webhook_url: "https://hooks.slack.com/services/..."
```

### Telegram
```yaml
notifications:
  telegram:
    token: "BOT_TOKEN"
    chat_id: "CHAT_ID"
```

## 🛠️ CLI Reference

You can override most configuration settings directly from the command line.

```bash
ansible-autoprovisioner \
  --config rules.yml \     # Required
  --ui \                   # Enable Dashboard
  --interval 10 \          # Faster polling
  --max-retries 5 \        # More retries
  --dry-run \              # Validate only
  --verbose                # Debug logging
```

## 📊 State Model Detailed

The `state.json` file uses the following statuses:

1.  **`pending`**: Initial state. The system has decided this node needs work.
2.  **`running`**: Thread has been allocated and Ansible is actively executing.
3.  **`success`**: All assigned rules finished with exit code `0`.
4.  **`error`**: One or more rules failed after `max_retries`.
5.  **`orphaned`**: The instance was in state but is no longer returned by Any detector.