
# Ansible AutoProvisioner - Examples

## Basic Examples

### Example 1: Basic Web Server Provisioning

**Configuration** (`config.yaml`):
```yaml
rules:
  - name: "basic-web-server"
    match:
      groups: ["webservers"]
    playbook: "playbooks/basic-webserver.yml"
```

**Inventory** (`inventory.ini`):
```ini
[webservers]
web01.example.com ansible_host=192.168.1.10
web02.example.com ansible_host=192.168.1.11
```

**Playbook** (`playbooks/basic-webserver.yml`):
```yaml
---
- name: Provision basic web server
  hosts: all
  become: yes
  
  tasks:
    - name: Install nginx
      apt:
        name: nginx
        state: present
    
    - name: Start nginx service
      service:
        name: nginx
        state: started
        enabled: yes
```

**Run**:
```bash
python -m ansible_autoprovisioner.main --config config.yaml
```

### Example 2: Environment-Specific Provisioning

**Configuration**:
```yaml
rules:
  - name: "production-servers"
    match:
      vars:
        environment: "production"
    playbook: "playbooks/production-hardening.yml"
  
  - name: "staging-servers"
    match:
      vars:
        environment: "staging"
    playbook: "playbooks/staging-setup.yml"
```

**Inventory**:
```ini
[production]
prod-web01 ansible_host=192.168.1.100 environment=production
prod-db01  ansible_host=192.168.1.101 environment=production

[staging]
stage-web01 ansible_host=192.168.2.100 environment=staging
stage-db01  ansible_host=192.168.2.101 environment=staging
```

## Advanced Examples

### Example 3: Multi-Role Server Provisioning

**Configuration**:
```yaml
rules:
  # Database servers with backup enabled
  - name: "database-with-backup"
    match:
      groups: ["databases"]
      vars:
        backup_enabled: "true"
    playbook: "playbooks/database-with-backup.yml"
  
  # Application servers in production
  - name: "production-app-servers"
    match:
      groups: ["appservers"]
      vars:
        environment: "production"
    playbook: "playbooks/production-app.yml"
  
  # Monitoring for all production servers
  - name: "production-monitoring"
    match:
      vars:
        environment: "production"
    playbook: "playbooks/monitoring-agent.yml"
```

**Inventory**:
```ini
[databases]
db-primary   ansible_host=192.168.1.20 environment=production backup_enabled=true
db-secondary ansible_host=192.168.1.21 environment=production backup_enabled=true
db-test      ansible_host=192.168.1.22 environment=staging

[appservers]
app01 ansible_host=192.168.1.30 environment=production
app02 ansible_host=192.168.1.31 environment=staging

# All production servers get monitoring
[production:children]
databases
appservers
```

### Example 4: Complex Group Matching

**Configuration**:
```yaml
rules:
  # Match any server in load balancer pool
  - name: "load-balancer-members"
    match:
      groups: ["lb-pool-1", "lb-pool-2", "lb-pool-3"]
    playbook: "playbooks/lb-member-config.yml"
  
  # Match servers with specific application tags
  - name: "wordpress-servers"
    match:
      groups: ["webservers"]
      vars:
        application: "wordpress"
        version: "6.0"
    playbook: "playbooks/wordpress-setup.yml"
```
