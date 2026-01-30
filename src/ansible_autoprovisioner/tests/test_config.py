import tempfile
import yaml
from pathlib import Path
from ansible_autoprovisioner.config import DaemonConfig
def create_test_config(config_dict):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_dict, f)
        return f.name
def test_new_format_with_named_rules():
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
            }
        },
        'groups': {
            'web-servers': {
                'match': {
                    'role': 'web',
                    'environment': 'production'
                },
                'jump_host': {
                    'instance': 'i-bastion123'
                },
                'key': './production.pem',
                'rules': ['base-setup', 'install-nginx']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        assert len(config.rules) == 2
        assert 'base-setup' in config.rules
        assert 'install-nginx' in config.rules
        nginx_rule = config.rules['install-nginx']
        assert nginx_rule.playbook == 'playbooks/nginx.yml'
        assert nginx_rule.match['os'] == 'ubuntu'
        assert nginx_rule.vars['nginx_version'] == '1.18'
        assert len(config.groups) == 1
        assert 'web-servers' in config.groups
        web_group = config.groups['web-servers']
        assert web_group.match['role'] == 'web'
        assert web_group.match['environment'] == 'production'
        assert web_group.jump_host == {'instance': 'i-bastion123'}
        assert web_group.key == './production.pem'
        assert web_group.rules == ['base-setup', 'install-nginx']
        web_rules = config.get_rules_for_group('web-servers')
        assert len(web_rules) == 2
        assert web_rules[0].name == 'base-setup'
        assert web_rules[1].name == 'install-nginx'
        config.validate()
        print("✓ New format with named rules passed")
    finally:
        Path(config_file).unlink()
def test_backward_compatibility_old_format():
    config_data = {
        'rules': [
            {
                'name': 'old-rule-1',
                'playbook': 'playbooks/old1.yml',
                'match': {'type': 'old'},
                'vars': {'version': '1.0'}
            }
        ],
        'groups': {
            'old-group': {
                'match': {'type': 'old'},
                'rules': ['old-rule-1']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        assert len(config.rules) == 1
        assert 'old-rule-1' in config.rules
        old_group = config.groups['old-group']
        assert old_group.rules == ['old-rule-1']
        print("✓ Backward compatibility with old format passed")
    finally:
        Path(config_file).unlink()
def test_inline_rules_in_groups():
    config_data = {
        'groups': {
            'inline-group': {
                'match': {},
                'rules': [
                    {
                        'name': 'inline-rule',
                        'playbook': 'playbooks/inline.yml',
                        'vars': {'inline': True}
                    }
                ]
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        assert 'inline-rule' in config.rules
        assert config.rules['inline-rule'].playbook == 'playbooks/inline.yml'
        assert config.rules['inline-rule'].vars['inline'] == True
        inline_group = config.groups['inline-group']
        assert inline_group.rules == ['inline-rule']
        print("✓ Inline rules in groups passed")
    finally:
        Path(config_file).unlink()
def test_mixed_rules_formats():
    config_data = {
        'rules': {
            'named-rule': {
                'playbook': 'playbooks/named.yml'
            }
        },
        'groups': {
            'mixed-group': {
                'match': {},
                'rules': [
                    'named-rule',
                    {
                        'name': 'inline-rule',
                        'playbook': 'playbooks/inline.yml'
                    }
                ]
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        assert 'named-rule' in config.rules
        assert 'inline-rule' in config.rules
        mixed_group = config.groups['mixed-group']
        assert 'named-rule' in mixed_group.rules
        assert 'inline-rule' in mixed_group.rules
        print("✓ Mixed rules formats passed")
    finally:
        Path(config_file).unlink()
def test_validation_missing_rule():
    config_data = {
        'groups': {
            'test-group': {
                'match': {},
                'rules': ['non-existent-rule']
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        try:
            config.validate()
            print("❌ Should have raised ValueError for missing rule")
            return False
        except ValueError as e:
            assert "references unknown rule" in str(e)
            assert "non-existent-rule" in str(e)
            print("✓ Validation catches missing rules passed")
    finally:
        Path(config_file).unlink()
def test_empty_config():
    config_data = {}
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        assert len(config.detectors) == 0
        assert len(config.rules) == 0
        assert len(config.groups) == 0
        config.validate()
        print("✓ Empty config passed")
    finally:
        Path(config_file).unlink()
def test_jump_host_variations():
    test_cases = [
        (None, None),
        ({'instance': 'i-12345'}, {'instance': 'i-12345'}),
        ({'vars': {'role': 'bastion'}}, {'vars': {'role': 'bastion'}}),
        ({'instance': ''}, {'instance': ''}),
    ]
    for jump_host_config, expected in test_cases:
        config_data = {
            'groups': {
                'test': {
                    'match': {},
                    'jump_host': jump_host_config,
                    'rules': []
                }
            }
        }
        config_file = create_test_config(config_data)
        try:
            config = DaemonConfig.load(config_file)
            group = config.groups['test']
            assert group.jump_host == expected
        finally:
            Path(config_file).unlink()
    print("✓ Jump host variations passed")
def test_get_group_for_instance():
    config_data = {
        'groups': {
            'production-web': {
                'match': {
                    'environment': 'production',
                    'role': 'web'
                },
                'rules': []
            },
            'staging-db': {
                'match': {
                    'environment': 'staging',
                    'role': 'database'
                },
                'rules': []
            }
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        prod_instance = {'environment': 'production', 'role': 'web'}
        assert config.get_group_for_instance(prod_instance) == 'production-web'
        staging_instance = {'environment': 'staging', 'role': 'database'}
        assert config.get_group_for_instance(staging_instance) == 'staging-db'
        other_instance = {'environment': 'dev', 'role': 'web'}
        assert config.get_group_for_instance(other_instance) is None
        partial_instance = {'environment': 'production'}
        assert config.get_group_for_instance(partial_instance) is None
        print("✓ Instance matching passed")
    finally:
        Path(config_file).unlink()
def test_complete_example():
    config_data = {
        'detectors': {
            'aws': {
                'regions': ['us-east-1', 'us-west-2']
            }
        },
        'rules': {
            'base-provision': {
                'playbook': 'playbooks/base.yml',
                'vars': {
                    'timezone': 'UTC',
                    'admin_user': 'ubuntu'
                }
            },
            'security-hardening': {
                'playbook': 'playbooks/security.yml',
                'match': {'security': 'enabled'},
                'vars': {
                    'fail2ban': True,
                    'firewall_ports': [22, 80, 443]
                }
            }
        },
        'groups': {
            'production-frontend': {
                'match': {
                    'environment': 'production',
                    'role': 'frontend'
                },
                'jump_host': {
                    'instance': 'i-bastion-prod'
                },
                'key': '/etc/ssh/keys/production.pem',
                'vars': {
                    'env': 'production',
                    'deployment_group': 'frontend'
                },
                'rules': [
                    'base-provision',
                    'security-hardening'
                ]
            },
            'staging-backend': {
                'match': {
                    'environment': 'staging',
                    'role': 'backend'
                },
                'jump_host': {
                    'vars': {'jump_host': True, 'environment': 'staging'}
                },
                'key': '/etc/ssh/keys/staging.pem',
                'vars': {
                    'env': 'staging',
                    'debug': True
                },
                'rules': [
                    'base-provision',
                    {
                        'name': 'custom-backend-setup',
                        'playbook': 'playbooks/custom-backend.yml',
                        'vars': {'api_port': 8080}
                    }
                ]
            }
        },
        'daemon': {
            'interval': 60,
            'state_file': '/var/lib/autoprovisioner/state.json',
            'log_dir': '/var/log/autoprovisioner',
            'max_retries': 5,
            'ui': True
        }
    }
    config_file = create_test_config(config_data)
    try:
        config = DaemonConfig.load(config_file)
        config.validate()
        assert len(config.detectors) == 1
        assert len(config.rules) == 3
        assert len(config.groups) == 2
        assert 'base-provision' in config.rules
        assert 'security-hardening' in config.rules
        assert 'custom-backend-setup' in config.rules
        prod_frontend = config.groups['production-frontend']
        assert prod_frontend.jump_host == {'instance': 'i-bastion-prod'}
        assert prod_frontend.key == '/etc/ssh/keys/production.pem'
        assert len(prod_frontend.rules) == 2
        assert 'security-hardening' in prod_frontend.rules
        staging_backend = config.groups['staging-backend']
        assert 'custom-backend-setup' in staging_backend.rules
        custom_rule = config.rules['custom-backend-setup']
        assert custom_rule.playbook == 'playbooks/custom-backend.yml'
        assert custom_rule.vars['api_port'] == 8080
        staging_rules = config.get_rules_for_group('staging-backend')
        assert len(staging_rules) == 2
        prod_instance = {'environment': 'production', 'role': 'frontend'}
        assert config.get_group_for_instance(prod_instance) == 'production-frontend'
        print("✓ Complete example passed")
    finally:
        Path(config_file).unlink()
if __name__ == '__main__':
    print("Testing Simplified Config - Phase 1")
    print("=" * 60)
    try:
        test_new_format_with_named_rules()
        test_backward_compatibility_old_format()
        test_inline_rules_in_groups()
        test_mixed_rules_formats()
        test_validation_missing_rule()
        test_empty_config()
        test_jump_host_variations()
        test_get_group_for_instance()
        test_complete_example()
        print("=" * 60)
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
