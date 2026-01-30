import sys
import logging
from ansible_autoprovisioner.daemon import ProvisioningDaemon
from ansible_autoprovisioner.config import DaemonConfig
from ansible_autoprovisioner.utils.cli import parse_arguments
from ansible_autoprovisioner.utils.logging import setup_logging
def main() -> int:
    args = parse_arguments()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    import os
    logger.info(f"Main start [PID: {os.getpid()}]")
    try:
        config = DaemonConfig.load(
            config_file=args.config,
            state_file=args.state_file,
            log_dir=args.log_dir,
            interval=args.interval,
            max_retries=args.max_retries,
            ui=args.ui
        )
        config.validate()
        if args.dry_run:
            logger.info("Configuration validated successfully (dry-run)")
            return 0
        daemon = ProvisioningDaemon(config)
        daemon.run()
        return 0
    except FileNotFoundError as e:
        logger.error("Configuration error: %s", e)
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception:
        logger.exception("Fatal error")
        return 1
if __name__ == "__main__":
    sys.exit(main())
