from .registry  import DetectorRegistry
import logging
class Notifier:
    def __init__(self,notifiers):
        self.notifiers = []
        for n in notifiers:
            try:
                self.notifiers.append(
                    NotifyRegistry.create(n.name, **d.options)
                )
            except Exception as e:
                logging.error(
                    "Notifier '%s' disabled: %s",
                    d.name,
                    e,
                )

    def notify_all(self):
        for n in self.notifiers:
            try:
                n.notify():
                    
            except Exception:
                logging.exception("Notifier %s failed during notify()",n)

        return True
