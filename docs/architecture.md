## Component Details

### 1. Detector System (`detectors/`)

**Purpose**: Discovers instances from various sources.

**Components**:
- `BaseDetector` (abstract class): Defines the detector interface
- `StaticDetector`: Reads instances from Ansible inventory files
- `DetectorManager`: Coordinates multiple detectors

**Workflow**:
1. Parses Ansible inventory files
2. Extracts host information (IP, groups, variables)
3. Creates `DetectedInstance` objects with unique instance IDs
4. Returns deduplicated list of instances

### 2. Rule Matcher (`matcher.py`)

**Purpose**: Matches detected instances against provisioning rules.

**Matching Criteria**:
- Host groups (e.g., `["webservers", "production"]`)
- Host variables (e.g., `{"environment": "production"}`)

**Behavior**:
- Evaluates each rule against each instance
- Returns list of playbooks to execute for matched instances
- Supports multiple matching rules per instance

### 3. State Manager (`state.py`)

**Purpose**: Tracks provisioning state to ensure idempotency.

**Key Features**:
- Persistent JSON-based state storage
- Thread-safe operations with locking
- Tracks instance status (NEW, PROVISIONING, PROVISIONED, FAILED, etc.)
- Manages playbook execution history
- Orphan detection (instances no longer in inventory)

**State Transitions**:
```
NEW → PROVISIONING → PROVISIONED (success)
                 → FAILED (failure)
                 → PARTIAL (partial success)
```

### 4. Ansible Executor (`executor.py`)

**Purpose**: Executes Ansible playbooks with proper error handling.

**Features**:
- Concurrent execution with ThreadPoolExecutor
- Comprehensive logging to file
- Retry logic with configurable limits
- Real-time output capture
- Error propagation and handling

**Execution Flow**:
1. Submits instances to thread pool
2. Runs playbooks sequentially for each instance
3. Captures stdout/stderr to log files
4. Updates state based on execution results
5. Stops execution on first failure (per instance)

### 5. Daemon Service (`daemon.py`)

**Purpose**: Provides continuous monitoring and provisioning.

**Operation Loop**:
```
while running:
    1. Detect instances from inventory
    2. Update state with new/removed instances
    3. Match instances against rules
    4. Execute provisioning for:
        - NEW instances
        - FAILED instances (retry)
    5. Sleep for configured interval
```

**Signal Handling**: Graceful shutdown on SIGINT/SIGTERM

### 6. Configuration System (`config.py`)

**Purpose**: Manages configuration loading and validation.

**Features**:
- YAML configuration file support
- Command-line argument integration
- Configuration validation
- Default value management

## Data Flow

```
1. Detection Phase
   Inventory File → StaticDetector → DetectedInstance objects

2. Matching Phase
   DetectedInstance + Rules → RuleMatcher → List[playbooks]

3. State Update Phase
   DetectedInstance + Playbooks → StateManager → Updated State

4. Execution Phase
   Instance + Playbooks → AnsibleExecutor → Playbook Execution

5. State Finalization
   Execution Results → StateManager → Final Status
```

## Design Principles

### 1. Idempotency
- State tracking prevents duplicate executions
- Playbook results are persisted and considered in retry decisions
- Instance status determines provisioning eligibility

### 2. Extensibility
- Detector system designed for pluggable implementations
- Rule system can be extended with new matching criteria
- State manager supports custom serialization

### 3. Observability
- Comprehensive logging at all levels
- Detailed execution logs stored per instance
- State file provides audit trail

### 4. Reliability
- Thread-safe state operations
- Transactional state updates
- Graceful error handling
- Configurable retry mechanisms
