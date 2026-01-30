import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
@dataclass
class Rule:
    name: str
    playbook: str
    match: Dict[str, Any] = field(default_factory=dict)
    vars: Dict[str, Any] = field(default_factory=dict)
@dataclass
class Group:
    name: str
    match: Dict[str, Any] = field(default_factory=dict)
    rules: List[str] = field(default_factory=list)
    jump_host: Optional[Dict[str, Any]] = None
    key: Optional[str] = None
    vars: Dict[str, Any] = field(default_factory=dict)
@dataclass
class DetectorConfig:
    name: str
    options: Dict[str, Any]

@dataclass
class NotifierConfig:
    name: str
    options: Dict[str, Any]
@dataclass
class DaemonConfig:
    config_file: str
    interval: int = 30
    state_file: str = "state.json"
    log_dir: str = "/var/log/ansible-autoprovisioner/"
    max_retries: int = 3
    ui: bool = True
    detectors: List[DetectorConfig] = field(default_factory=list)
    rules: Dict[str, Rule] = field(default_factory=dict)
    groups: Dict[str, Group] = field(default_factory=dict)
    notifications: List[NotifierConfig] = field(default_factory=list)
    def __post_init__(self):
        self._load_config()
    def _load_config(self):
        path = Path(self.config_file)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        daemon_data = data.get('daemon', {})
        self.interval = daemon_data.get('interval', self.interval)
        self.state_file = daemon_data.get('state_file', self.state_file)
        self.log_dir = daemon_data.get('log_dir', self.log_dir)
        self.max_retries = daemon_data.get('max_retries', self.max_retries)
        self.ui = daemon_data.get('ui', self.ui)
        detectors_data = data.get('detectors', {})
        for name, options in detectors_data.items():
            self.detectors.append(DetectorConfig(name=name, options=options))
        
        notifications_data = data.get('notifications', {})
        if isinstance(notifications_data, dict):
            for name, options in notifications_data.items():
                self.notifications.append(NotifierConfig(name=name, options=options))
        elif isinstance(notifications_data, list):
            for item in notifications_data:
                if isinstance(item, dict) and 'name' in item:
                    self.notifications.append(NotifierConfig(name=item['name'], options=item.get('options', {})))
        rules_data = data.get('rules', {})
        if isinstance(rules_data, list):
            for rule_data in rules_data:
                rule_name = rule_data['name']
                self.rules[rule_name] = Rule(
                    name=rule_name,
                    playbook=rule_data['playbook'],
                    match=rule_data.get('match', {}),
                    vars=rule_data.get('vars', {})
                )
        elif isinstance(rules_data, dict):
            for rule_name, rule_data in rules_data.items():
                self.rules[rule_name] = Rule(
                    name=rule_name,
                    playbook=rule_data['playbook'],
                    match=rule_data.get('match', {}),
                    vars=rule_data.get('vars', {})
                )
        groups_data = data.get('groups', {})
        for group_name, group_data in groups_data.items():
            rule_names = []
            for rule_ref in group_data.get('rules', []):
                if isinstance(rule_ref, str):
                    rule_names.append(rule_ref)
                elif isinstance(rule_ref, dict) and 'name' in rule_ref:
                    rule_name = rule_ref['name']
                    if rule_name not in self.rules:
                        self.rules[rule_name] = Rule(
                            name=rule_name,
                            playbook=rule_ref['playbook'],
                            match=rule_ref.get('match', {}),
                            vars=rule_ref.get('vars', {})
                        )
                    rule_names.append(rule_name)
            group = Group(
                name=group_name,
                match=group_data.get('match', {}),
                rules=rule_names,
                jump_host=group_data.get('jump_host'),
                key=group_data.get('key'),
                vars=group_data.get('vars', {})
            )
            self.groups[group_name] = group
    @classmethod
    def load(cls, config_file: str, **overrides) -> 'DaemonConfig':
        config = cls(config_file=config_file)
        for key, value in overrides.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        return config
    def validate(self):
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
        for rule in self.get_all_rules():
            self._validate_playbook_path(rule.playbook)
        for group in self.groups.values():
            if group.key and not Path(group.key).exists():
                logger.warning(f"SSH key not found: {group.key}")
        for group_name, group in self.groups.items():
            for rule_name in group.rules:
                if rule_name not in self.rules:
                    raise ValueError(
                        f"Group '{group_name}' references unknown rule: '{rule_name}'"
                    )
        logger.info(f"Configuration loaded successfully")
        logger.info(f"  Detectors: {len(self.detectors)}")
        logger.info(f"  Rules: {len(self.rules)}")
        logger.info(f"  Groups: {len(self.groups)}")
        logger.info(f"  Notifications: {len(self.notifications)}")
        logger.info(f"  Interval: {self.interval}s")
        return True
    def _validate_playbook_path(self, playbook_path: str):
        path = Path(playbook_path)
        if not path.exists():
            if not path.is_absolute():
                config_dir = Path(self.config_file).parent
                abs_path = config_dir / path
                if abs_path.exists():
                    return
                abs_path = Path.cwd() / path
                if abs_path.exists():
                    return
            logger.warning(f"Playbook not found: {playbook_path}")
    def get_rules_for_group(self, group_name: str) -> List[Rule]:
        if group_name not in self.groups:
            return []
        group = self.groups[group_name]
        rules = []
        for rule_name in group.rules:
            if rule_name in self.rules:
                rules.append(self.rules[rule_name])
        return rules
    def get_all_rules(self) -> List[Rule]:
        all_rules = []
        for group_name in self.groups:
            all_rules.extend(self.get_rules_for_group(group_name))
        return all_rules
    def get_group_for_instance(self, instance_tags: Dict[str, Any]) -> Optional[str]:
        for group_name, group in self.groups.items():
            if self._matches(group.match, instance_tags):
                return group_name
        return None
    def _matches(self, match_criteria: Dict[str, Any], instance_vars: Dict[str, Any]) -> bool:
        for key, expected_value in match_criteria.items():
            if key not in instance_vars:
                return False
            if instance_vars[key] != expected_value:
                return False
        return True
    def has_groups(self) -> bool:
        return len(self.groups) > 0
    def to_dict(self) -> Dict[str, Any]:
        return {
            'config_file': self.config_file,
            'interval': self.interval,
            'state_file': self.state_file,
            'log_dir': self.log_dir,
            'max_retries': self.max_retries,
            'ui': self.ui,
            'detectors': [{'name': d.name, 'options': d.options} for d in self.detectors],
            'rules': {name: rule.name for name, rule in self.rules.items()},
            'groups': {
                name: {
                    'name': group.name,
                    'match': group.match,
                    'rules': group.rules,
                    'jump_host': group.jump_host,
                    'key': group.key,
                    'vars': group.vars
                }
                for name, group in self.groups.items()
            },
            'notifications': [{'name': n.name, 'options': n.options} for n in self.notifications]
        }
