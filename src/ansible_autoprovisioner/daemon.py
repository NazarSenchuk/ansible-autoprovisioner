import logging
import signal
import time

from ansible_autoprovisioner.config import DaemonConfig
from ansible_autoprovisioner.detectors import DetectorManager
from ansible_autoprovisioner.executor import AnsibleExecutor
from ansible_autoprovisioner.matcher import RuleMatcher
from ansible_autoprovisioner.notifications.notifier import NotifierManager
from ansible_autoprovisioner.state import StateManager, InstanceStatus
from ansible_autoprovisioner.utils.api import ApiInterface
from ansible_autoprovisioner.utils.ui import UIServer

logger = logging.getLogger(__name__)


class ProvisioningDaemon:
    def __init__(self, config: DaemonConfig):
        self.config = config
        self.ui_server = None
        self.running = False
        self.notifier = None

        logger.info("Daemon Start")
        self.state = StateManager(state_file=config.state_file)
        self.detectors = DetectorManager(config.detectors)
        self.matcher = RuleMatcher(self.config)
        self.executor = AnsibleExecutor(self.state, self.config)
        self.management = ApiInterface(self.state, self.config)

        if len(self.config.notifications):
            self.notifier = NotifierManager(self.config.notifications)

        if self.config.ui:
            self.start_ui()

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, s, f):
        logger.info(f"Signal {s}")
        self.running = False

    def run(self):
        self.running = True
        logger.info("Running loop")
        try:
            self._run_loop()
        except KeyboardInterrupt:
            logger.info("Interrupt")
        except Exception:
            logger.exception("Crash")
            raise
        finally:
            self._cleanup()

    def _run_loop(self):
        while self.running:
            logger.info("Detecting...")
            detected = self.detectors.detect_all()
            det_ids = {d.instance_id for d in detected}
            state_insts = self.state.get_instances()
            state_ids = {s.instance_id for s in state_insts}

            for inst in detected:
                groups, tasks = self.matcher.match(inst)
                current_inst = self.state.get_instance(inst.instance_id)

                if inst.instance_id not in state_ids:
                    if not tasks:
                        logger.warning(f"Ignored {inst.instance_id}: No matching playbooks")
                        continue
                    self.state.detect_instance(
                        instance_id=inst.instance_id,
                        ip=inst.ip_address,
                        detector=inst.detector,
                        tags=inst.tags,
                        groups=groups,
                        playbook_tasks=tasks
                    )
                    logger.info(f"New {inst.instance_id} ({len(tasks)} tasks)")

                elif (len(current_inst.playbook_tasks) != len(tasks) or
                      current_inst.groups != groups):
                    self.state.update_instance(
                        instance_id=inst.instance_id,
                        groups=groups,
                        playbook_tasks=tasks
                    )
                    logger.info(f"Updated {inst.instance_id} ({len(tasks)} tasks)")

            for s_inst in state_insts:
                if (s_inst.instance_id not in det_ids and
                        s_inst.overall_status != InstanceStatus.ORPHANED):
                    logger.info(f"Orphaned {s_inst.instance_id}")
                    self.state.mark_final_status(s_inst.instance_id, InstanceStatus.ORPHANED)

            logger.info("Reconciling...")

            pending = self.state.get_instances(status=InstanceStatus.PENDING)
            if pending:
                logger.info(f"Prioritizing {len(pending)} PENDING instances")
                self.executor.provision(pending)

            failed = self.state.get_instances(status=InstanceStatus.FAILED)
            if failed:
                logger.info(f"Retrying {len(failed)} FAILED instances")
                self.executor.provision(failed)

            if self.notifier:
                self._check_notifications()

            if self.running and self.config.interval > 0:
                time.sleep(self.config.interval)

    def start_ui(self):
        try:
            self.ui_server = UIServer(
                management=self.management,
            )
            if not self.ui_server.start():
                logger.warning("UI fail")
        except Exception:
            logger.exception("UI error")

    def _cleanup(self):
        self.state.mark_all_running_failed()
        self.executor.shutdown()
        if self.ui_server:
            self.ui_server.stop()
        logger.info("Daemon stop")

    def _check_notifications(self):
        final_statuses = (
            InstanceStatus.SUCCESS,
            InstanceStatus.PARTIAL_FAILURE,
            InstanceStatus.FAILED
        )
        for inst in self.state.get_instances():
            if inst.overall_status in final_statuses and not inst.notified:
                details = None
                if inst.overall_status != InstanceStatus.SUCCESS:
                    failed_tasks = [
                        n for n, r in inst.playbook_results.items()
                        if r.status == "error"
                    ]
                    if failed_tasks:
                        details = f"Failed tasks: {', '.join(failed_tasks)}"

                sent = self.notifier.notify_all(inst, inst.overall_status.value, details)
                if sent > 0:
                    logger.info(
                        f"Notification sent for {inst.instance_id} ({inst.overall_status.value})"
                    )

                self.state.mark_notified(inst.instance_id)
