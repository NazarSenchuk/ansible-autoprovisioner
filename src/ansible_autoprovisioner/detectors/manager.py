class DetectorManager:
    def __init__(self, detectors):
        self.detectors = detectors

    def detect_all(self):
        instances = {}

        for detector in self.detectors:
            for inst in detector.detect():
                instances[inst.instance_id] = inst

        return list(instances.values())
