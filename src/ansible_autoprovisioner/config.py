import yaml
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class Rule:

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
class DetectorConfig:
    name: str
    options: {}
    @classmethod
    def from_dict(cls, name , cfg):
        if not isinstance(cfg , dict):
            raise ValueError(f"Detector {name}  must be a  mapping ")
        return cls(name , cfg )
        

@dataclass
class DaemonConfig:
    
    config: str
    ui: bool = True
    interval: int = 30
    state_file: str = "state.json"
    log_dir: str = "/tmp/ansible-autoprovisioner/logs/"
    max_retries: int = 3
    detectors: List[DetectorConfig] = field(default_factory=lambda: [DetectorConfig(name = "static" ,options = {"inventory" :"inventory.ini"} )])
    rules: List[Rule] = field(default_factory=list, init=False, repr=False)
    
    def __post_init__(self):
        self._load_rules()
        self._load_detectors()

    
    def _load_rules(self):
        config_path = Path(self.config)
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f) or {}
                self.rules = [
                    Rule.from_dict(rule_data) 
                    for rule_data in yaml_data.get('rules', [])
                ]

    def _load_detectors(self):
        config_path = Path(self.config)
        if not config_path.exists():
            return

        with open(config_path) as f:
            yaml_data = yaml.safe_load(f) or {}

        self.detectors = [
            DetectorConfig.from_dict(name, cfg)
            for name, cfg in yaml_data.get("detectors", {}).items()
        ]
    
    @classmethod
    def load(cls, config_file: str, **overrides) -> 'DaemonConfig':        
        defaults = {
            'interval': 30,
            'state_file': 'state.json',
            'log_dir': 'logs',
            'detectors': ['static']
        }

        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path) as f:
                yaml_data = yaml.safe_load(f) or {}
                defaults.update(yaml_data.get('daemon', {}))
        
        defaults.update({k: v for k, v in overrides.items() if v is not None})
        
        return cls(config=config_file, **defaults)
    
    def validate(self):
       
        rules_path = Path(self.config)
        if not rules_path.exists():
            raise FileNotFoundError(f"Rules not found: {rules_path}")
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        
        for rule in self.rules:
            
            playbook_path = Path(rule.playbook)

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
        print(f"  {len(self.rules)} rules")
        print(f"  Interval: {self.interval}s")