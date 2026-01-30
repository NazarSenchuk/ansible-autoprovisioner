from .registry  import DetectorRegistry
import logging
class DetectorManager:
    def __init__(self, detectors):
        self.detectors = []
        for d in detectors:
            try:
                self.detectors.append(
                    DetectorRegistry.create(d.name, **d.options)
                )
            except Exception as e:
                logging.error(
                    "Detector '%s' disabled: %s",
                    d.name,
                    e,
                )
    def detect_all(self):
        instances = {}
        for detector in self.detectors:
            try:
                for inst in detector.detect():
                    instances[inst.instance_id] = inst
            except Exception:
                logging.exception("Detector %s failed during detect()", detector)
        return list(instances.values())
