import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from ansible_autoprovisioner.state import InstanceStatus, PlaybookStatus
from ansible_autoprovisioner.config import DaemonConfig
import tempfile

logger = logging.getLogger(__name__)


class AnsibleExecutor:
    def __init__(self, state, config: DaemonConfig , max_workers: int  = 4):
        self.state = state
        self.pool = ThreadPoolExecutor(max_workers=max_workers)
        self.config = config

    def provision(self, instances: list):
        if not instances:
            return

        for inst in instances:
            if inst.overall_status == InstanceStatus.PROVISIONING:
                continue

            self.state.mark_provisioning(inst.instance_id)
            future = self.pool.submit(self._run_instance, inst)
            future.add_done_callback(self._handle_error)

    def _handle_error(self, future):
        try:
            future.result()
        except Exception as e:
            logger.error(f"Provisioning thread crashed: {e}", exc_info=True)

    def _run_instance(self, instance  ):
        instance_log_dir = Path(self.config.log_dir) / instance.instance_id
        instance_log_dir.mkdir(parents=True, exist_ok=True)

        for playbook in instance.playbooks:
            logger.info(
                f"Running playbook {playbook} on {instance.instance_id}"
            )

            playbook_state = self.state.start_playbook(
                instance.instance_id,
                name=Path(playbook).stem,
                file=playbook,
            )

            if playbook_state.retry_count > self.config.max_retries:
                logger.error(
                    f"Playbook {playbook} exceeded retry limit on {instance.instance_id}"
                )
                self.state.mark_final_status(
                    instance.instance_id,
                    InstanceStatus.FAILED,
                )
                return

            rc = self._run_playbook(instance, playbook)

            if rc != 0:
                self.state.finish_playbook(
                    instance.instance_id,
                    playbook_state,
                    PlaybookStatus.FAILED,
                    error=f"{playbook} failed with rc={rc}",
                )
                self.state.mark_final_status(
                    instance.instance_id,
                    InstanceStatus.FAILED,
                )
                return

            self.state.finish_playbook(
                instance.instance_id,
                playbook_state,
                PlaybookStatus.SUCCESS,
            )

        self.state.mark_final_status(
            instance.instance_id,
            InstanceStatus.PROVISIONED,
        )

    def _run_playbook(self, instance, playbook: str) -> int:
        log_file =Path(self.config.log_dir) / instance.instance_id / f"{Path(playbook).stem}.log"

        inventory_path = self._write_temp_inventory(instance)

        cmd = [
            "ansible-playbook",
            playbook,
            "-i", str(inventory_path),
        ]

        with open(log_file, "a") as lf:
            lf.write(f"\n=== {datetime.utcnow()} START {playbook} ===\n")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            output = []
            for line in process.stdout:
                lf.write(line)
                output.append(line)

            rc = process.wait()
            lf.write(f"\n=== END rc={rc} ===\n")

        if any("no hosts matched" in l.lower() for l in output):
            logger.error("No hosts matched for %s", instance.instance_id)
            rc = 2

        inventory_path.unlink(missing_ok=True)

        return rc

    def _write_temp_inventory(self, instance) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".ini",
            prefix="ansible-inventory-",
            delete=False,
        )

        groups = instance.groups or ["all"]

        for group in groups:
            tmp.write(f"[{group}]\n")
            tmp.write(f"{instance.ip_address}\n\n")

        tmp.write("[all:vars]\n")
        tmp.write("ansible_user=ubuntu\n")
        tmp.write("ansible_ssh_common_args='-o StrictHostKeyChecking=no'\n")
        tmp.write("ansible_python_interpreter=/usr/bin/python3\n")

        tmp.flush()
        tmp.close()

        return Path(tmp.name)
