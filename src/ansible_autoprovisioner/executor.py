import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from ansible_autoprovisioner.state import InstanceStatus,PlaybookStatus
logger = logging.getLogger(__name__)
class AnsibleExecutor:
    def __init__(self, state, inventory: str, log_dir: str, max_workers: int = 4):
        self.state = state
        self.inventory = inventory
        self.log_dir = Path(log_dir)
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def provision(self, instances: list):
        if not instances:
            return
        futures = []
        for inst in instances:
            if inst.overall_status == InstanceStatus.PROVISIONING:
                continue
            
            self.state.mark_provisioning(inst.instance_id)
            futures.append(self.pool.submit(self._run_instance, inst))

        for future in as_completed(futures):
            future.result()  # raise exception if any

    def _run_instance(self, instance):
        instance_log_dir = self.log_dir / instance.instance_id
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
            if playbook_state.retry_count > 3:
                logger.error(
                    f"Playbook {name} exceeded retry limit on {instance.instance_id}"
                )
                self.state.mark_final_status(
                    instance.instance_id,
                    InstanceStatus.FAILED,
                )
                return

            rc = self._run_playbook(instance, playbook, instance_log_dir)

            if rc != 0:

                self.state.finish_playbook(
                    instance.instance_id,
                    playbook_state,
                    PlaybookStatus.FAILED,
                    error=f"{playbook} failed with rc={rc}",
                )

                # stop execution immediately
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


    def _run_playbook(self, instance, playbook: str, log_dir: Path) -> int:
        log_file = log_dir / f"{Path(playbook).stem}.log"

        cmd = [
            "ansible-playbook",
            playbook,
            "-i", self.inventory,
            "-l", instance.ip_address,
            "-e", f"instance_id={instance.instance_id}",
        ]

        with open(log_file, "a") as lf:
            lf.write(f"\n=== {datetime.utcnow()} START {playbook} ===\n")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            for line in process.stdout:
                lf.write(line)

            rc = process.wait()
            lf.write(f"\n=== END rc={rc} ===\n")

        return rc
