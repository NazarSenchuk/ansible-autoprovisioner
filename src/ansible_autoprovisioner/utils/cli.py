
import argparse


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ansible Auto-Provisioner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        required=True,
        help="Path to rules YAML configuration file",
    )

    parser.add_argument(
        "--inventory",
        default="inventory.ini",
        help="Path to Ansible inventory file (default: inventory.ini)",
    )

    parser.add_argument(
        "--state-file",
        default="state.json",
        help="Path to state file (default: state.json)",
    )

    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory for logs (default: logs)",
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Polling interval in seconds (default: 60)",
    )

    parser.add_argument(
        "--ui",
        type=bool,
        default=True,
        help="Whether enable UI",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retries per playbook (default: 3)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and exit without running",
    )

    return parser.parse_args()
