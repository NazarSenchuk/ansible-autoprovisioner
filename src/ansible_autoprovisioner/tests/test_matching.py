import tempfile
import yaml
from pathlib import Path
from ansible_autoprovisioner.config import DaemonConfig
from ansible_autoprovisioner.matcher import RuleMatcher
from ansible_autoprovisioner.detectors.base import DetectedInstance
def create_test_config(config_dict):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_dict, f)
        return f.name
def test_matching_logic():
    config_data = {
        'rules': {
            'base-setup': {
                'playbook': 'playbooks/base.yml',
                'vars': {'timezone': 'UTC'}
            },
            'install-nginx': {
                'playbook': 'playbooks/nginx.yml',
                'match': {'os': 'ubuntu'},
                'vars': {'nginx_version': '1.18'}
            },
            'install-postgres': {
                'playbook': 'playbooks/postgres.yml',
                'match': {'db': 'postgres'},
                'vars': {'postgres_version': '14'}
            }
        },
        'groups': {
            'production-web': {
                'match': {
                    'environment': 'production',
                    'role': 'web'
                },
                'jump_host': {
                    'instance': 'i-bastion-prod'
                },
                'key': '/keys/production.pem',
                'vars': {
                    'env': 'production',
                    'monitoring': 'enabled'
                },
                'rules': ['base-setup', 'install-nginx']
            },
            'staging-db': {
                'match': {
                    'environment': 'staging',
                    'role': 'database'
                },
                'key': '/keys/staging.pem',
                'vars': {'env': 'staging'},
                'rules': ['base-setup', 'install-postgres']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        matcher = RuleMatcher(config)
        instance1 = DetectedInstance(
            instance_id="i-web-1",
            ip_address="10.0.1.10",
            detector="aws",
            tags={
                'environment': 'production',
                'role': 'web',
                'os': 'ubuntu'
            }
        )
        group_infos, playbook_tasks = matcher.match(instance1)
        assert len(group_infos) == 1
        assert group_infos[0].name == 'production-web'
        assert group_infos[0].key == '/keys/production.pem'
        assert group_infos[0].jump_host == {'instance': 'i-bastion-prod'}
        assert len(playbook_tasks) == 2
        task_names = {t.name for t in playbook_tasks}
        assert 'base-setup' in task_names
        assert 'install-nginx' in task_names
        nginx_task = [t for t in playbook_tasks if t.name == 'install-nginx'][0]
        assert nginx_task.file == 'playbooks/nginx.yml'
        assert nginx_task.group == 'production-web'
        assert nginx_task.key == '/keys/production.pem'
        assert nginx_task.jump_host == {'instance': 'i-bastion-prod'}
        assert nginx_task.vars['nginx_version'] == '1.18'
        assert nginx_task.vars['env'] == 'production'
        assert nginx_task.vars['monitoring'] == 'enabled'
        assert 'os' not in nginx_task.vars
        assert 'environment' not in nginx_task.vars
        assert 'role' not in nginx_task.vars
        instance2 = DetectedInstance(
            instance_id="i-db-1",
            ip_address="10.0.2.10",
            detector="aws",
            tags={
                'environment': 'staging',
                'role': 'database',
                'db': 'postgres'
            }
        )
        group_infos2, playbook_tasks2 = matcher.match(instance2)
        assert len(group_infos2) == 1
        assert group_infos2[0].name == 'staging-db'
        assert group_infos2[0].key == '/keys/staging.pem'
        assert group_infos2[0].jump_host is None
        assert len(playbook_tasks2) == 2
        task_names2 = {t.name for t in playbook_tasks2}
        assert 'base-setup' in task_names2
        assert 'install-postgres' in task_names2
        instance3 = DetectedInstance(
            instance_id="i-no-match",
            ip_address="10.0.3.10",
            detector="aws",
            tags={'environment': 'development'}
        )
        group_infos3, playbook_tasks3 = matcher.match(instance3)
        assert len(group_infos3) == 0
        assert len(playbook_tasks3) == 0
        print("✓ Matching logic passed")
    finally:
        Path(config_file).unlink()
def test_rule_level_matching():
    config_data = {
        'rules': {
            'ubuntu-only': {
                'playbook': 'playbooks/ubuntu.yml',
                'match': {'os': 'ubuntu'},
                'vars': {'ubuntu_version': '20.04'}
            },
            'centos-only': {
                'playbook': 'playbooks/centos.yml',
                'match': {'os': 'centos'},
                'vars': {'centos_version': '8'}
            },
            'always-run': {
                'playbook': 'playbooks/always.yml',
                'vars': {'always': True}
            }
        },
        'groups': {
            'test': {
                'match': {'env': 'test'},
                'vars': {'test_mode': True},
                'rules': ['ubuntu-only', 'centos-only', 'always-run']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        matcher = RuleMatcher(config)
        ubuntu_instance = DetectedInstance(
            instance_id="i-ubuntu",
            ip_address="10.0.1.1",
            detector="static",
            tags={'env': 'test', 'os': 'ubuntu'}
        )
        group_infos, playbook_tasks = matcher.match(ubuntu_instance)
        assert len(playbook_tasks) == 2
        ubuntu_task = [t for t in playbook_tasks if t.name == 'ubuntu-only'][0]
        always_task = [t for t in playbook_tasks if t.name == 'always-run'][0]
        assert ubuntu_task.vars['ubuntu_version'] == '20.04'
        assert ubuntu_task.vars['test_mode'] == True
        assert always_task.vars['always'] == True
        assert always_task.vars['test_mode'] == True
        centos_instance = DetectedInstance(
            instance_id="i-centos",
            ip_address="10.0.1.2",
            detector="static",
            tags={'env': 'test', 'os': 'centos'}
        )
        group_infos2, playbook_tasks2 = matcher.match(centos_instance)
        assert len(playbook_tasks2) == 2
        task_names2 = {t.name for t in playbook_tasks2}
        assert 'centos-only' in task_names2
        assert 'always-run' in task_names2
        assert 'ubuntu-only' not in task_names2
        print("✓ Rule-level matching passed")
    finally:
        Path(config_file).unlink()
def test_variable_merging():
    config_data = {
        'rules': {
            'test-rule': {
                'playbook': 'playbooks/test.yml',
                'vars': {
                    'rule_var': 'from_rule',
                    'common': 'rule_value'
                }
            }
        },
        'groups': {
            'test-group': {
                'match': {'env': 'test'},
                'vars': {
                    'group_var': 'from_group',
                    'common': 'group_value',
                },
                'rules': ['test-rule']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        matcher = RuleMatcher(config)
        instance = DetectedInstance(
            instance_id="i-test",
            ip_address="10.0.1.1",
            detector="static",
            tags={'env': 'test'}
        )
        group_infos, playbook_tasks = matcher.match(instance)
        assert len(playbook_tasks) == 1
        task = playbook_tasks[0]
        assert task.vars['rule_var'] == 'from_rule'
        assert task.vars['group_var'] == 'from_group'
        assert task.vars['common'] == 'rule_value'
        assert 'env' not in task.vars
        print("✓ Variable merging passed")
    finally:
        Path(config_file).unlink()
def test_empty_group_match():
    config_data = {
        'rules': {
            'test': {
                'playbook': 'playbooks/test.yml',
                'vars': {'default': True}
            }
        },
        'groups': {
            'catch-all': {
                'match': {},
                'vars': {'catch_all': True},
                'rules': ['test']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        matcher = RuleMatcher(config)
        instance = DetectedInstance(
            instance_id="i-any",
            ip_address="10.0.1.1",
            detector="aws",
            tags={}
        )
        group_infos, playbook_tasks = matcher.match(instance)
        assert len(group_infos) == 1
        assert len(playbook_tasks) == 1
        task = playbook_tasks[0]
        assert task.vars['catch_all'] == True
        assert task.vars['default'] == True
        print("✓ Empty group match (catch-all) passed")
    finally:
        Path(config_file).unlink()
def test_multiple_groups_matching():
    config_data = {
        'rules': {
            'common': {
                'playbook': 'playbooks/common.yml',
                'vars': {'common': True}
            },
            'web-specific': {
                'playbook': 'playbooks/web.yml',
                'match': {'subrole': 'web'},
                'vars': {'app_type': 'web'}
            },
            'db-specific': {
                'playbook': 'playbooks/db.yml',
                'match': {'subrole': 'db'},
                'vars': {'app_type': 'database'}
            }
        },
        'groups': {
            'production': {
                'match': {'environment': 'production'},
                'key': '/keys/production.pem',
                'vars': {'env': 'production'},
                'rules': ['common']
            },
            'webservers': {
                'match': {'role': 'server'},
                'jump_host': {'instance': 'i-jump'},
                'vars': {'server_type': 'general'},
                'rules': ['common', 'web-specific']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        matcher = RuleMatcher(config)
        instance = DetectedInstance(
            instance_id="i-multi",
            ip_address="10.0.1.100",
            detector="aws",
            tags={
                'environment': 'production',
                'role': 'server',
                'subrole': 'web'
            }
        )
        group_infos, playbook_tasks = matcher.match(instance)
        assert len(group_infos) == 2
        group_names = {g.name for g in group_infos}
        assert 'production' in group_names
        assert 'webservers' in group_names
        assert len(playbook_tasks) == 3
        print("✓ Multiple groups matching passed")
    finally:
        Path(config_file).unlink()
if __name__ == '__main__':
    print("Testing Matching Logic with Tags/Vars Separation")
    print("=" * 60)
    try:
        test_matching_logic()
        test_rule_level_matching()
        test_variable_merging()
        test_empty_group_match()
        test_multiple_groups_matching()
        print("=" * 60)
        print("✅ All Matching tests passed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
