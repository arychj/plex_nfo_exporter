from pathlib import Path

class PathMapper:
    def __init__(self, config):
        self.mappings = config["path_mapping"]

    def map_path(self, path):
        for path_list in self.mappings:
            path = str(path).replace(path_list.get("plex"), path_list.get("local"))

        return Path(path)
