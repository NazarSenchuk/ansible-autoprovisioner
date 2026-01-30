import fnmatch
from typing import List, Dict, Any
from ansible_autoprovisioner.config import DaemonConfig, Rule, Group
from ansible_autoprovisioner.detectors.base import DetectedInstance
from ansible_autoprovisioner.state import GroupInfo, PlaybookTask
def match_instance_to_groups(instance: DetectedInstance, config: DaemonConfig) -> List[GroupInfo]:
    matched = []
    for group_name, group in config.groups.items():
        if tags_match_criteria(instance.tags, group.match):
            matched.append(GroupInfo(
                name=group_name,
                key=group.key,
                jump_host=group.jump_host,
                vars=group.vars,
                rules=group.rules
            ))
    return matched
def create_playbook_tasks(instance: DetectedInstance, config: DaemonConfig) -> List[PlaybookTask]:
    matched_groups = match_instance_to_groups(instance, config)
    tasks = []
    for group_info in matched_groups:
        for rule_name in group_info.rules:
            if rule_name in config.rules:
                rule = config.rules[rule_name]
                if tags_match_criteria(instance.tags, rule.match):
                    tasks.append(create_task(rule, group_info))
    return tasks
def tags_match_criteria(tags: Dict[str, str], criteria: Dict[str, Any]) -> bool:
    if not criteria:
        return True
    for key, expected_value in criteria.items():
        if key not in tags:
            return False
        tag_value = str(tags[key])
        pattern = str(expected_value)
        if not fnmatch.fnmatch(tag_value, pattern):
            return False
    return True
def create_task(rule: Rule, group_info: GroupInfo) -> PlaybookTask:
    task_vars = {**group_info.vars, **rule.vars}
    return PlaybookTask(
        name=rule.name,
        file=rule.playbook,
        group=group_info.name,
        key=group_info.key,
        jump_host=group_info.jump_host,
        vars=task_vars
    )
class RuleMatcher:
    def __init__(self, config: DaemonConfig):
        self.config = config
    def match(self, instance: DetectedInstance):
        groups = match_instance_to_groups(instance, self.config)
        tasks = create_playbook_tasks(instance, self.config)
        return groups, tasks
