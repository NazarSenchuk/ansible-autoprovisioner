from typing import List
from .base import BaseDetector, DetectedInstance
import logging
logger = logging.getLogger(__name__)
class AWSDetector(BaseDetector):
    def __init__(self, region):
        self.region = region
        logger.info("Initializing AWS Detector")
        self._require_boto3()
        self._require_credentials()
    def _require_boto3(self):
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError(
                "AWSDetector requires boto3. Install with: pip install boto3"
            ) from e
    def _require_credentials(self):
        import boto3
        try:
            sts = boto3.client("sts", region_name=self.region)
            sts.get_caller_identity()
        except Exception as e:
            raise RuntimeError(
                "AWS credentials not found. Configure via aws configure / env vars / IAM role"
            ) from e
    def detect(self) -> List[DetectedInstance]:
        import boto3
        ec2 = boto3.client("ec2", region_name=self.region)
        response = ec2.describe_instances(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )
        instances = []
        for reservation in response.get("Reservations", []):
            for inst in reservation.get("Instances", []):
                ip =inst.get("PublicIpAddress") or inst.get("PrivateIpAddress")
                if not ip:
                    continue
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                instances.append(
                    DetectedInstance(
                        instance_id=f"aws-{inst['InstanceId']}",
                        ip_address=ip,
                        detector="aws",
                        tags={
                            **tags,
                            "aws_instance_id": inst["InstanceId"],
                            "aws_region": self.region,
                            "aws_az": inst["Placement"]["AvailabilityZone"],
                        },
                    )
                )
        return instances
