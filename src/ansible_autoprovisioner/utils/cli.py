import argparse
import json
import sys
from typing import Optional

import yaml

from ..config import DaemonConfig
from ..state import StateManager
from .api import ApiInterface


def parse_arguments():
    parser = argparse.ArgumentParser(description="Ansible Auto-Provisioner Daemon")
    parser.add_argument("--config", required=True, help="Path to config YAML file")
    parser.add_argument("--state-file", help="Override state file path")
    parser.add_argument("--log-dir", help="Override log directory")
    parser.add_argument("--interval", type=int, help="Polling interval seconds")
    parser.add_argument("--max-retries", type=int, help="Max retries")
    parser.add_argument("--ui", action="store_true", help="Enable UI")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate config and exit"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    return parser.parse_args()


def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ansible Auto-Provisioner Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    list_parser = subparsers.add_parser('list', help='List instances')
    list_parser.add_argument(
        '--status',
        help='Filter by status'
    )
    list_parser.add_argument(
        '--format',
        choices=['table', 'json', 'yaml'],
        default='table',
        help='Output format'
    )
    list_parser.add_argument(
        '--config',
        required=True,
        help='Path to configuration file'
    )

    add_parser = subparsers.add_parser('add', help='Add instance manually')
    add_parser.add_argument('--config', required=True, help='Path to configuration file')
    add_parser.add_argument('--instance-id', required=True, help='Instance ID')
    add_parser.add_argument('--ip-address', required=True, help='IP address')
    add_parser.add_argument('--groups', nargs='*', default=[], help='Groups')
    add_parser.add_argument('--playbooks', nargs='*', default=[], help='Playbooks')
    add_parser.add_argument('--tags', nargs='*', default=[], help='Tags (key=value)')

    details_parser = subparsers.add_parser('details', help='Show instance details')
    details_parser.add_argument('--config', required=True, help='Path to configuration file')
    details_parser.add_argument('instance_id', help='Instance ID')
    details_parser.add_argument(
        '--format', choices=['json', 'yaml'], default='json', help='Output format'
    )

    retry_parser = subparsers.add_parser('retry', help='Retry provisioning')
    retry_parser.add_argument('--config', required=True, help='Path to configuration file')
    retry_parser.add_argument('instance_id', help='Instance ID')

    delete_parser = subparsers.add_parser('delete', help='Delete instance')
    delete_parser.add_argument('--config', required=True, help='Path to configuration file')
    delete_parser.add_argument('instance_id', help='Instance ID')
    delete_parser.add_argument('--force', action='store_true', help='Force delete')

    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--config', required=True, help='Path to configuration file')
    stats_parser.add_argument(
        '--format', choices=['table', 'json', 'yaml'], default='table', help='Output format'
    )

    return parser


def load_config(config_path: str) -> DaemonConfig:
    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)
    return DaemonConfig.from_dict(config_data)


def parse_tags(tags_list: list) -> dict:
    tags = {}
    for tag in tags_list:
        if '=' in tag:
            key, value = tag.split('=', 1)
            tags[key.strip()] = value.strip()
    return tags


def print_table(data, headers):
    col_widths = []
    for i, header in enumerate(headers):
        max_len = len(header)
        for row in data:
            if i < len(row):
                max_len = max(max_len, len(str(row[i])))
        col_widths.append(max_len + 2)

    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    print(header_line)
    print("-" * len(header_line))
    for row in data:
        row_line = " | ".join(str(cell).ljust(w) for cell, w in zip(row, col_widths))
        print(row_line)


def main():
    parser = create_cli_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        config = load_config(args.config)
        state = StateManager(state_file=config.state_file)
        api = ApiInterface(state, config)

        if args.command == 'list':
            instances = api.list_instances(args.status)
            if args.format == 'json':
                print(json.dumps([i.to_dict() for i in instances], indent=2))
            elif args.format == 'yaml':
                print(yaml.dump([i.to_dict() for i in instances], default_flow_style=False))
            else:
                headers = ["ID", "IP", "Status", "Groups", "Playbooks", "Updated"]
                rows = []
                for inst in instances:
                    rows.append([
                        inst.instance_id,
                        inst.ip_address,
                        inst.overall_status.value.upper(),
                        ', '.join([g.name for g in inst.groups]),
                        len(inst.playbook_tasks),
                        inst.updated_at.isoformat() if inst.updated_at else 'N/A'
                    ])
                print_table(rows, headers)

        elif args.command == 'add':
            tags = parse_tags(args.tags)
            result = api.add_instance(
                instance_id=args.instance_id,
                ip_address=args.ip_address,
                groups=args.groups,
                tags=tags,
                playbooks=args.playbooks
            )
            if result['success']:
                print(f"✓ Instance {args.instance_id} added")
            else:
                print(f"✗ Failed: {result['error']}")
                sys.exit(1)

        elif args.command == 'details':
            result = api.get_instance_details(args.instance_id)
            if not result['success']:
                print(f"✗ {result['error']}")
                sys.exit(1)
            if args.format == 'json':
                print(json.dumps(result, indent=2))
            else:
                print(yaml.dump(result, default_flow_style=False))

        elif args.command == 'retry':
            result = api.retry_instance(args.instance_id)
            if result['success']:
                print(f"✓ Retry requested for {args.instance_id}")
            else:
                print(f"✗ {result['error']}")
                sys.exit(1)

        elif args.command == 'delete':
            result = api.delete_instance(args.instance_id, args.force)
            if result['success']:
                print(f"✓ Instance {args.instance_id} deleted")
            else:
                print(f"✗ {result['error']}")
                sys.exit(1)

        elif args.command == 'stats':
            stats = api.get_stats()
            if args.format == 'json':
                print(json.dumps(stats, indent=2))
            elif args.format == 'yaml':
                print(yaml.dump(stats, default_flow_style=False))
            else:
                print("\n=== Statistics ===\n")
                print(f"Total: {stats['total_instances']}")
                print(f"Successful: {stats['successful']}")
                print(f"Failed: {stats['failed']}")
                print(f"Running: {stats['running']}")
                print(f"Pending: {stats['pending']}")
                print(f"Orphaned: {stats['orphaned']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
