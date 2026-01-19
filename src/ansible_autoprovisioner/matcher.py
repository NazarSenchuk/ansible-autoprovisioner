from typing import List
from ansible_autoprovisioner.config import Rule
from ansible_autoprovisioner.detectors.base import DetectedInstance


class RuleMatcher:
    def __init__(self, rules: List[Rule]):
        self.rules = rules

    def match(self, inst: DetectedInstance) -> List[str]:
        playbooks = []

        for rule in self.rules:
            if self._match_rule(rule, inst):
            
                playbooks.append(rule.playbook)

        return playbooks

    def _match_rule(self, rule: Rule, inst: DetectedInstance) -> bool:
        match = rule.match or {}

        
        groups = match.get("groups")
        if groups:
            if not any(g in inst.groups for g in groups):
                return False

        vars_match = match.get("vars")
        if vars_match:
            for k, v in vars_match.items():
                if inst.vars.get(k) != v:
                    return False

        return True
