import datetime, os

class AgeChecker:
    def __init__(self, config):
        self.point_in_time = datetime.datetime.now()
        self.locked_days = config["days_difference"]
    
    def is_locked(self, file):
        return False
        if not os.path.exists(file):
            return False
        
        file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file))
        time_difference = self.point_in_time - file_mod_time
                            
        return time_difference.days < self.locked_days
