# Usage Examples

This guide provides real-world patterns for configuring Ansible AutoProvisioner.

## 1. The "Auto-Scaling Web" Pattern
In this scenario, you have servers scaling up in AWS. You want them configured with Nginx as soon as they appear.

**rules.yml**:
```yaml
detectors:
  aws:
    region: "us-east-1"

rules:
  - name: "nginx-setup"
    playbook: "./ansible/nginx.yml"

groups:
  web-nodes:
    match:
      aws_tag_Role: "Web"
      aws_tag_Environment: "Production"
    rules:
      - "nginx-setup"

notifications:
  slack:
    webhook_url: "https://hooks.slack.com/services/..."
```

## 2. Multi-Stage Provisioning
Run a series of playbooks in order when a new host is added.

**rules.yml**:
```yaml
rules:
  - name: "base-os"
    playbook: "./playbooks/base.yml"
  - name: "app-runtime"
    playbook: "./playbooks/python.yml"
  - name: "app-deploy"
    playbook: "./playbooks/deploy.yml"

groups:
  app-servers:
    match:
      group: "apps"
    rules:
      - "base-os"      # Runs 1st
      - "app-runtime"  # Runs 2nd
      - "app-deploy"   # Runs 3rd
```

## 3. Mixed Environment Support
Managing both Cloud (AWS) and Hybrid (On-Premise static) resources in one daemon.

**rules.yml**:
```yaml
detectors:
  aws:
    region: "us-west-2"
  static:
    inventory: "/etc/ansible/hosts"

groups:
  monitoring:
    match:
      os_family: "Debian"
    rules:
      - "install-prometheus-agent"
```

## 4. Troubleshooting Failure
When a host is in `ERROR` status, you can check its logs:

1. Go to the UI at `http://localhost:8080`.
2. Find the failed instance.
3. Click "Logs" to see exactly which Ansible task failed.
4. Fix the issue in your playbook.
5. Click "Retry" in the UI to reset its status to `PENDING`.

## 5. Security & Isolation
Running with a non-root user and custom log path.

```bash
ansible-autoprovisioner \
  --config production.yml \
  --log-dir /home/devops/logs/provisioner \
  --state-file /home/devops/data/state.json
```
