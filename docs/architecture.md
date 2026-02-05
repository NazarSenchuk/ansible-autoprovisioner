# Architecture Documentation

## 🏗️ System Overview

Ansible AutoProvisioner is a state-driven automation daemon designed for infrastructure lifecycle management. It uses a prioritized execution model to ensure new resources are provisioned immediately while maintaining a robust retry mechanism for failures.

## 🧱 Component Architecture

### 1. Detector System (`detectors/`)
**Purpose**: Continuous discovery of infrastructure from multiple sources.
- **AWS Detector**: Discovers EC2 instances via tags and metadata.
- **Static Detector**: Parses standard Ansible inventory files.
- **Detector Manager**: Aggregates and deduplicates results from all active detectors.

### 2. State Management (`state.py`)
The "Brain" of the system.
- **Persistence**: Saves state to `state.json` atomically.
- **Status Lifecycle**:
  - `PENDING`: Ready to be provisioned (new or retry-queued).
  - `RUNNING`: Handled by an Ansible worker.
  - `SUCCESS`: Goal achieved.
  - `ERROR`: Logic failure or max retries hit.
  - `ORPHANED`: Host vanished from source but still in state.
- **Thread Safety**: Uses file-level and object-level locking to prevent race conditions during concurrent execution.

### 3. Rule Matcher (`matcher.py`)
**Purpose**: Mapping detected instances to playbooks using flexible criteria.
- Supports matching by host groups and arbitrary tags/variables.
- Allows multiple playbooks to be assigned to a single instance.

### 4. Execution Engine (`executor.py`)
The "Hands" of the system.
- Uses `ansible-runner` (or direct subprocess) to execute playbooks.
- **Isolation**: Each instance gets its own worker thread and log directory.
- **Telemetry**: Captures real-time output and streams it to `.log` files.

### 5. Notification System (`notifications/`)
The "Voice" of the system.
- **Standardized Interface**: Allows pluggable notifiers (Slack, Telegram, etc.).
- **Deduplication**: Tracks the `notified` status to ensure you only get one alert per terminal status.

## 🔄 Data Flow Diagram

```mermaid
graph TD
    subgraph Discovery
    A[AWS API] --> D[Detector Manager]
    B[Inventory File] --> D
    end

    subgraph Logic
    D -- Detected List --> E[State Manager]
    E -- Previous State Reference --> F[Rule Matcher]
    F -- Task List --> G[Daemon Controller]
    end

    subgraph Execution
    G -- Prioritize PENDING --> H[Ansible Executor]
    G -- Retry ERROR --> H
    H -- Success/Fail --> E
    H -- Logs --> I[Filesystem]
    end

    subgraph Alerting
    E -- Terminal State --> J[Notification Manager]
    J --> K[Slack/Telegram]
    end
```

## �️ Design Principles

- **Idempotency**: The system ensures playbooks are only run when necessary and tracks history to avoid infinite loops.
- **Crash Consistency**: Persistent state ensures that if the process dies, it resumes exactly where it stopped.
- **Scalability**: Thread-pooled execution allows handling hundreds of instances concurrently without blocking the main monitoring loop.
- **Flexibility**: Decoupling detectors from executors allows the system to easily add new infrastructure sources (GCP, Azure, etc.).
