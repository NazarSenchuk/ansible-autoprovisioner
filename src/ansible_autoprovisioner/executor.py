import subprocess
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
import tempfile
from ansible_autoprovisioner.state import InstanceState, InstanceStatus, PlaybookStatus, GroupInfo
from ansible_autoprovisioner.config import DaemonConfig

logger = logging.getLogger(__name__)

class AnsibleExecutor:
    def __init__(self, state, config: DaemonConfig, max_workers: int = 4):
        self.state = state
        self.config = config
        self.pool = ThreadPoolExecutor(max_workers=max_workers)

    def provision(self, instances: list):
        for inst in instances:
            if inst.overall_status in (InstanceStatus.RUNNING, InstanceStatus.SUCCESS):
                continue

            total_retries = sum(p.retry_count for p in inst.playbook_results.values())
            if total_retries >= self.config.max_retries:
                logger.error(f"Max retries hit for {inst.instance_id}")
                self.state.mark_final_status(inst.instance_id, InstanceStatus.ERROR)
                continue

            logger.info(f"Provisioning {inst.instance_id}")
            self.state.mark_running(inst.instance_id)
            self.pool.submit(self._run_instance, inst)

    def _run_instance(self, instance):
        try:
            for task in instance.playbook_tasks:
                existing = instance.playbook_results.get(task.name)
                if existing and existing.status == PlaybookStatus.SUCCESS:
                    continue

                playbook_state = self.state.start_playbook(
                    instance.instance_id,
                    name=task.name,
                    file=task.file
                )

                rc = self._run_playbook(instance, task)

                if rc != 0:
                    self.state.finish_playbook(
                        instance.instance_id,
                        playbook_state,
                        PlaybookStatus.ERROR,
                        error=f"Exit {rc}"
                    )
                    self.state.mark_final_status(instance.instance_id, InstanceStatus.ERROR)
                    return

                self.state.finish_playbook(instance.instance_id, playbook_state, PlaybookStatus.SUCCESS)

            self.state.mark_final_status(instance.instance_id, InstanceStatus.SUCCESS)
        except Exception:
            logger.exception(f"Error provisioning {instance.instance_id}")
            self.state.mark_final_status(instance.instance_id, InstanceStatus.ERROR)

    def _run_playbook(self, instance, task) -> int:
        inventory_path = None
        try:
            inventory_path = self._write_temp_inventory(instance, task)
            log_dir = Path(self.config.log_dir) / instance.instance_id
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"{task.name}.log"
            
            cmd = ["ansible-playbook", str(task.file), "-i", str(inventory_path), "-v"]
            
            with open(log_file, "a") as lf:
                lf.write(f"\n=== {datetime.utcnow()} START {task.name} ===\n")
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    bufsize=1
                )
                for line in process.stdout:
                    lf.write(line)
                    logger.debug(f"[{instance.instance_id}] {line.strip()}")
                rc = process.wait()
                lf.write(f"\n=== END rc={rc} ===\n")
            return rc
        except Exception:
            logger.exception(f"Fail {task.name}")
            return 1
        finally:
            if inventory_path and inventory_path.exists():
                try:
                    inventory_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def _write_temp_inventory(self, instance, task) -> Path:
        try:
            group = next((g for g in instance.groups if g.name == task.group), None)
            ansible_user = (
                task.vars.get("ansible_user") or 
                (group.vars.get("ansible_user") if group else None) or 
                instance.tags.get("ansible_user") or 
                "ubuntu"
            )
            ssh_key = (
                task.key or 
                (group.key if group else None) or 
                instance.tags.get("ansible_ssh_private_key_file")
            )
            
            if ssh_key and "~" in str(ssh_key):
                ssh_key = Path(ssh_key).expanduser()
                
            jump_host = task.jump_host or (group.jump_host if group else None)
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False, encoding='utf-8')
            
            tmp.write(f"[{task.group}]\n{instance.ip_address}\n\n[all:vars]\n")
            tmp.write(f"ansible_user={ansible_user}\n")
            tmp.write("ansible_python_interpreter=/usr/bin/python3\n")
            tmp.write("ansible_host_key_checking=False\n")
            tmp.write("ansible_ssh_timeout=30\n")
            
            if ssh_key and Path(ssh_key).exists():
                tmp.write(f"ansible_ssh_private_key_file={ssh_key}\n")
                
            ssh_args = ["-o StrictHostKeyChecking=no", "-o UserKnownHostsFile=/dev/null"]
            if jump_host:
                if isinstance(jump_host, str):
                    proxy_cmd = f'ssh -W %h:%p -q {jump_host}'
                elif isinstance(jump_host, dict):
                    u = jump_host.get('user', ansible_user)
                    h = jump_host.get('host')
                    p = jump_host.get('port', 22)
                    ident = f"-i {ssh_key}" if ssh_key and Path(ssh_key).exists() else ""
                    proxy_cmd = f'ssh {ident} -W %h:%p -q -p {p} {u}@{h}'
                else:
                    proxy_cmd = ""
                if proxy_cmd:
                    ssh_args.append(f'-o ProxyCommand="{proxy_cmd}"')
            
            tmp.write(f"ansible_ssh_common_args='{' '.join(ssh_args)}'\n")
            for k, v in instance.tags.items():
                if isinstance(v, (str, int, float, bool)):
                    tmp.write(f"{k}={v}\n")
            
            tmp.flush()
            tmp.close()
            return Path(tmp.name)
        except Exception:
            logger.exception("Inv error")
            raise

    def shutdown(self):
        self.pool.shutdown(wait=True)
        logger.info("Executor shutdown")