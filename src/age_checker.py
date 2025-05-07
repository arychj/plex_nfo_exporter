import datetime, os
from typing import Any, Dict

class AgeChecker:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.point_in_time = datetime.datetime.now()
        self.locked_days = config["days_difference"]
    
    def is_locked(self, file: str) -> bool:
        locked = False

        if self.locked_days > -1 and os.path.exists(file):
            file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file))
            time_difference = self.point_in_time - file_mod_time
            locked = time_difference.days < self.locked_days
        
        return locked
