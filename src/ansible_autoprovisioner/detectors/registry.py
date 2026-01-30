class DetectorRegistry:
    _registry = {}
    @classmethod
    def create(cls, name: str, **options):
        if name not in cls._registry:
            raise ValueError(f"Unknown detector: {name}")
        return cls._registry[name](**options)
    @classmethod
    def register(cls , name  , detector_cls):
        if name in cls._registry:
            raise ValueError(f"Detector {name} already registered")
        cls._registry[name]  =  detector_cls
    @classmethod
    def available(cls):
        return  list(cls._registry.keys())
