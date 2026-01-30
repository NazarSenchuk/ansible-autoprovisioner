class NotifierRegistry:
    _registry = {}

    @classmethod
    def create(cls, name: str, **options):
        if name not in cls._registry:
            raise ValueError(f"Unknown notifier: {name}")
        return cls._registry[name](**options)

    @classmethod
    def register(cls, name: str, notifier_cls):
        cls._registry[name] = notifier_cls

    @classmethod
    def available(cls):
        return list(cls._registry.keys())
