import os
import json
import tempfile
import pytest
from datetime import datetime
from pathlib import Path
from ansible_autoprovisioner.state import (
    StateManager, 
    InstanceStatus, 
    PlaybookStatus, 
    PlaybookResult,
    GroupInfo,
    PlaybookTask
)

def test_playbook_result_serialization():
    res = PlaybookResult(
        name="test",
        file="test.yml",
        status=PlaybookStatus.SUCCESS,
        started_at=datetime.utcnow(),
        retry_count=1
    )
    data = res.to_dict()
    assert data["name"] == "test"
    assert data["status"] == "success"
    assert data["retry_count"] == 1
    
    res2 = PlaybookResult.from_dict(data)
    assert res2.name == "test"
    assert res2.status == PlaybookStatus.SUCCESS
    assert res2.retry_count == 1

def test_state_loading_save():
    state_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False).name
    try:
        with open(state_file, 'w') as f:
            json.dump({}, f)
            
        state = StateManager(state_file=state_file)
        state.detect_instance("i-123", "192.168.1.1")
        state.save_state()
        
        state2 = StateManager(state_file=state_file)
        inst = state2.get_instance("i-123")
        assert inst is not None
        assert inst.ip_address == "192.168.1.1"
        assert inst.overall_status == InstanceStatus.PENDING
    finally:
        if os.path.exists(state_file):
            os.remove(state_file)

def test_state_methods():
    state_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False).name
    try:
        with open(state_file, 'w') as f:
            json.dump({}, f)
            
        state = StateManager(state_file=state_file)
        instance = state.detect_instance(
            instance_id="i-123",
            ip="192.168.1.1",
            tags={"test": "true"}
        )
        assert instance.overall_status == InstanceStatus.PENDING
        
        state.mark_running("i-123")
        assert state.get_instance("i-123").overall_status == InstanceStatus.RUNNING
        
        state.mark_final_status("i-123", InstanceStatus.SUCCESS)
        assert state.get_instance("i-123").overall_status == InstanceStatus.SUCCESS
        
        p_res = state.start_playbook("i-123", "setup", "setup.yml")
        assert p_res.status == PlaybookStatus.RUNNING
        assert state.get_instance("i-123").overall_status == InstanceStatus.RUNNING
        
        state.finish_playbook("i-123", p_res, PlaybookStatus.SUCCESS)
        assert p_res.status == PlaybookStatus.SUCCESS
    finally:
        if os.path.exists(state_file):
            os.remove(state_file)

def test_state_edge_cases():
    state_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False).name
    try:
        with open(state_file, 'w') as f:
            json.dump({}, f)
            
        state = StateManager(state_file=state_file)
        instance1 = state.detect_instance(
            instance_id="i-1",
            ip="192.168.1.1",
            tags={"id": "1"}
        )
        instance2 = state.detect_instance(
            instance_id="i-2",
            ip="192.168.1.2",
            tags={"id": "2"}
        )
        
        instances = state.get_instances()
        assert len(instances) == 2
        
        state.delete_instance("i-1")
        instances = state.get_instances()
        assert len(instances) == 1
        assert instances[0].instance_id == "i-2"
        
        state.mark_running("i-2")
        state.mark_all_running_failed()
        assert state.get_instance("i-2").overall_status == InstanceStatus.ERROR
    finally:
        if os.path.exists(state_file):
            os.remove(state_file)

def test_state_status_filtering():
    state_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False).name
    try:
        with open(state_file, 'w') as f:
            json.dump({}, f)
            
        state = StateManager(state_file=state_file)
        state.detect_instance("i-pending", "192.168.1.1", tags={"status": "pending"})
        state.detect_instance("i-error", "192.168.1.2", tags={"status": "error"})
        state.detect_instance("i-running", "192.168.1.3", tags={"status": "running"})
        
        state.mark_running("i-running")
        state.mark_final_status("i-error", InstanceStatus.ERROR)
        
        pending_insts = state.get_instances(status=InstanceStatus.PENDING)
        assert len(pending_insts) == 1
        assert pending_insts[0].instance_id == "i-pending"
        
        running_insts = state.get_instances(status=InstanceStatus.RUNNING)
        assert len(running_insts) == 1
        assert running_insts[0].instance_id == "i-running"
    finally:
        if os.path.exists(state_file):
            os.remove(state_file)

def test_state_serialization():
    state_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False).name
    try:
        state = StateManager(state_file=state_file)
        group_info = GroupInfo(name="web")
        task = PlaybookTask(name="setup", file="setup.yml", group="web")
        
        state.detect_instance(
            instance_id="i-123456",
            ip="10.0.0.1",
            groups=[group_info],
            playbook_tasks=[task]
        )
        state.save_state()
        
        new_state = StateManager(state_file=state_file)
        loaded = new_state.get_instance("i-123456")
        assert loaded.instance_id == "i-123456"
        assert len(loaded.groups) == 1
        assert loaded.groups[0].name == "web"
        assert len(loaded.playbook_tasks) == 1
        assert loaded.playbook_tasks[0].name == "setup"
    finally:
        if os.path.exists(state_file):
            os.remove(state_file)
