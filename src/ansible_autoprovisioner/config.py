#!/usr/bin/env python3
import yaml
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class Rule:
    """Provisioning rule configuration."""
    name: str
    match: Dict[str, Dict[str, str]]
    playbook: str

    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Rule':
        return cls(
            name=data['name'],
            match=data.get('match', {}),
            playbook=data['playbook'],
        )

@dataclass
class DaemonConfig:
    
    config: str
    ui: bool = True
    static_inventory: str = "inventory.ini"
    interval: int = 30
    state_file: str = "state.json"
    log_dir: str = "logs"
    max_retries: int = 3
    detectors: List[str] = field(default_factory=lambda: ["static"])
    rules: List[Rule] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        self._load_rules()
    
    def _load_rules(self):
        config_path = Path(self.config)
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f) or {}
                self.rules = [
                    Rule.from_dict(rule_data) 
                    for rule_data in yaml_data.get('rules', [])
                ]
    
    @classmethod
    def load(cls, config_file: str, **overrides) -> 'DaemonConfig':        
        defaults = {
            'interval': 30,
            'state_file': 'state.json',
            'log_dir': 'logs',
            'max_retries': 3,
            'static_inventory': 'inventory.ini',
            'detectors': ['static']
        }
        
        # Load YAML config
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f) or {}
                defaults.update(yaml_data.get('daemon', {}))
        
        # Apply CLI overrides (filter out None values)
        defaults.update({k: v for k, v in overrides.items() if v is not None})
        
        return cls(config=config_file, **defaults)
    
    def validate(self):
        """Validate configuration"""
        # Check inventory file
        inventory = Path(self.static_inventory)
        if not inventory.exists():
            raise FileNotFoundError(f"Inventory not found: {inventory}")
        
        # Check rules file
        rules_path = Path(self.config)
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules not found: {rules_path}")
        
        # Create log directory
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        # Validate rules and playbooks
        for rule in self.rules:
            
            playbook_path = Path(rule.playbook)
            
            # Check if playbook exists (try absolute and relative paths)
            if not playbook_path.exists():
                if not playbook_path.is_absolute():
                    abs_path = Path.cwd() / playbook_path
                    if abs_path.exists():
                        rule.playbook = str(abs_path)
                    else:
                        print(f"Warning: Playbook not found: {rule.playbook}")
                else:
                    print(f"Warning: Playbook not found: {rule.playbook}")
        
        print(f"✓ Configuration loaded successfully")
        print(f"  • {len(self.rules)} rules")
        print(f"  • Inventory: {self.static_inventory}")
        print(f"  • Interval: {self.interval}s")