import hashlib, io, json
from pathlib import Path
from typing import Any, Dict, Union
from PIL.Image import Image

from logger import Logger

class FileRegistry:
    def __init__(self, config: Dict[str, Any], logger: Logger):
        self.logger = logger
        self._init_registry(config)

    def write(self, file_path: str, file_contents: Union[bytes, str, Image]) -> bool:
        if isinstance(file_contents, str):
            file_contents = file_contents.encode("utf-8")
        if isinstance(file_contents, Image):
            buffer = io.BytesIO()
            file_contents.save(buffer, format="jpeg")
            file_contents = buffer.getvalue()

        path = Path(file_path).resolve()
        path_str = str(path)
        registry = self._get_registry(path)

        content_hash = self._hash_content(file_contents)

        if path_str in registry:
            if registry[path_str] == content_hash:
                return False

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(file_contents)

        registry[path_str] = content_hash

        return True

    def save(self) -> None:
        for base_path, registry in self.registry.items():
            registry_path = self._get_registry_path(base_path)
            if registry_path.parent.exists():
                with open(registry_path, "w", encoding="utf-8") as f:
                    json.dump(registry, f, indent=2)
                    self.logger.info(f"[SUCCESS] Seved registry for {base_path}")

    def _init_registry(self, config: Dict[str, Any]) -> None:
        self.registry = {}
        for path_mapping in config["path_mapping"]:
            registry_contents = {}
            base_path = Path(path_mapping["local"]).resolve()
            
            registry_file = self._get_registry_path(base_path)
            if registry_file.exists():
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry_contents = json.load(f)

            self.registry[base_path] = registry_contents
            
    def _get_registry(self, path: str) -> Dict[str, str]:
        for key in self.registry.keys():
            if path.is_relative_to(key):
                return self.registry[key]
        
        raise Exception(f"Unregisted path: {path}")
    
    def _get_registry_path(self, base_path: Union[str, Path]) -> Path:
        if isinstance(base_path, str):
            base_path = Path(base_path)

        return base_path / "_nfo_registry.json"
    
    def _hash_content(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
    