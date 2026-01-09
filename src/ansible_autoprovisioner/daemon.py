#!/usr/bin/env python3

import signal
import time
import logging
from datetime import datetime
from typing import Optional
from ansible_autoprovisioner.detectors.base import DetectedInstance
from ansible_autoprovisioner.config import DaemonConfig
from ansible_autoprovisioner.state import StateManager, InstanceStatus, PlaybookResult, PlaybookStatus
from ansible_autoprovisioner.detectors import StaticDetector, DetectorManager
from ansible_autoprovisioner.matcher import RuleMatcher
from ansible_autoprovisioner.executor import AnsibleExecutor
from ansible_autoprovisioner.utils.ui import UIServer


logger = logging.getLogger(__name__)


class ProvisioningDaemon:
    def __init__(self, config: DaemonConfig):
        self.config = config
        logger.info(f"Starting Daemon")

        logger.info(f"Initializing ProvisioningDaemon")
        logger.info(f"  • State file: {config.state_file}")
        logger.info(f"  • Log directory: {config.log_dir}")
        logger.info(f"  • Inventory: {config.static_inventory}")
        logger.info(f"  • Interval: {config.interval}s")
        logger.info(f"  • Max retries: {config.max_retries}")
        self.state = StateManager(state_file=config.state_file)
        self.detectors  = DetectorManager([StaticDetector()])
        self.matcher = RuleMatcher(self.config.rules)
        self.executor = AnsibleExecutor(self.state , self.config.static_inventory , self.config.log_dir  )
        # Statistics
        self.stats = {
            'start_time': datetime.now(),
            'cycles': 0,
            'instances_processed': 0,
            'playbooks_executed': 0,
            'successful': 0,
            'failed': 0,
            'retried': 0
        }
        if self.config.ui:
            self.start_ui()
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _validate_playbooks(self):
        """Validate that all referenced playbooks exist"""
        logger.debug("Validating playbooks...")
        for rule in self.matcher.rules:
            if not rule.enabled:
                continue
                
            # Check if playbook exists
            import os
            playbook_path = rule.playbook
            if not os.path.exists(playbook_path):
                # Try relative to current directory
                if not os.path.isabs(playbook_path):
                    import os
                    cwd = os.getcwd()
                    absolute_path = os.path.join(cwd, playbook_path)
                    if os.path.exists(absolute_path):
                        rule.playbook = absolute_path
                        logger.debug(f"Found playbook at: {absolute_path}")
                    else:
                        logger.warning(f"Playbook not found: {playbook_path}")
                else:
                    logger.warning(f"Playbook not found: {playbook_path}")
    
    def _signal_handler(self, signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def run(self, once: bool = False):
        self.running = True
        logger.info(f"   Polling interval: {self.config.interval}s")
        logger.info("-" * 50)
        try:
            
            self._run_loop()
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        except Exception as e:
            logger.error(f"Daemon crashed: {e}", exc_info=True)
            raise
        finally:
            self._cleanup()
    
    def _run_loop(self):
        while self.running:
            
        

            # Check new instances  with detectors
            logger.info(f"Check new instance....")
            detected = self.detectors.detect_all()
            detected_ids = {d.instance_id for d in detected}

            state_instances = self.state.get_instances()
            state_ids = {s.instance_id for s in state_instances}

            for inst in detected:
                if inst.instance_id not in state_ids:
                
                    playbooks = self.matcher.match(inst)

                    self.state.detect_instance(
                        instance_id=inst.instance_id,
                        ip=inst.ip_address,
                        groups=inst.groups,
                        tags=inst.vars,
                        playbooks=playbooks,
                    )
                    logger.info(
                        f"Founded new {inst.instance_id} "
                        f"(playbooks: {playbooks})"
                    )


            # ORPHANED instances
            for inst in state_instances:
                if inst.instance_id not in detected_ids:
                    if inst.overall_status != InstanceStatus.ORPHANED:
                        logger.info(f"Instance orphaned: {inst.instance_id}")
                        self.state.mark_final_status(inst.instance_id, InstanceStatus.ORPHANED)

            # Provisioning new instance
            logger.info("Provisioning new instances...")
            self.executor.provision(self.state.get_instances(status=InstanceStatus.NEW))
            
            # Provisioning failure and partially  failure instances
            logger.info("Provisioning failed instances...")
            self.executor.provision(self.state.get_instances(status=InstanceStatus.FAILED))

            if self.running and self.config.interval > 0:
                time.sleep(self.config.interval)


    def start_ui(self):
        """Start the UI server if enabled"""
        try:
            self.ui_server = UIServer(
                daemon_ref=self,
            )
            if not self.ui_server.start():
                logger.warning("Failed to start UI server")
                self.ui_server = None
        except Exception as e:
            logger.error(f"Error starting UI server: {e}")
            self.ui_server = None
    
    def __cleanup(self):
        if self.ui_server:
            self.ui_server.stop()
        logger.info("Daemon stopped cleanly")
    
    