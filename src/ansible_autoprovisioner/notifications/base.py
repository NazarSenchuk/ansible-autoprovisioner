from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    @abstractmethod
    def notify(self, instance_id: str, status: str, details: str = None):
        pass
