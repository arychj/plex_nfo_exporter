import io, os

from pathlib import Path
from PIL import Image
from typing import Any, Dict, List

from logger import Logger
from age_checker import AgeChecker
from file_registry import FileRegistry
from path_mapper import PathMapper
from plex import Plex

class Exporter:
    def __init__(self, config: Dict[str, Any], plex: Plex, logger: Logger) -> None:
        self.config = config
        self.plex = plex
        self.logger = logger
        self.path_mapper = PathMapper(config)
        self.age_checker = AgeChecker(config)
        self.registry = FileRegistry(config, logger)
        
    def get_base_path(self, metadata, media_type: str) -> None:
        if media_type in ["movie", "episode"]:
            base_path = os.path.dirname(metadata.find("Media").find("Part").get("file"))
            base_path = Path(base_path)
        elif media_type == "season":
            m = self.plex.get_episodes(metadata)
            base_path = self.get_base_path(m[0], "episode")
        elif media_type == "tvshow":
            base_path = Path(metadata.find("Location").get("path"))

        base_path = self.path_mapper.map_path(base_path)

        return base_path

    def export(self, metadata, media_type: str) -> None:
        if self.config[f"export_{media_type}_nfo"]:
            try:
                base_path = self.get_base_path(metadata, media_type)
                nfo_path = base_path / self._get_nfo_name(metadata, media_type)

                if not self.age_checker.is_locked(nfo_path):
                    nfo_path.parent.mkdir(parents=True, exist_ok=True)

                    contents = []
                    for nfo_key, is_enabled in {**self.config["nfo"], **self._get_media_keys(media_type)}.items():
                        if is_enabled:
                            plex_key = self._get_plex_key(nfo_key, media_type)
                            if (item := metadata.get(plex_key)):
                                if nfo_key == "agent_id":
                                    if "themoviedb" in item:
                                        contents.append(f'<tmdbid>{item[item.rfind("//")+2:(item.rfind("?") if "?" in item else len(item))]}</tmdbid>')

                                    if "agents.hama" in item:
                                        contents.append(f'<{item[item.rfind("//")+2:item.rfind("-")]}id>{item[item.rfind("-")+1:(item.rfind("?") if "?" in item else len(item))]}</{item[item.rfind("//")+2:item.rfind("-")]}id>')

                                    for agent in metadata.findall('Guid'):
                                        agent_name = agent.get('id')[:agent.get('id').rfind(':')]+'id'
                                        agent_id = agent.get('id')[agent.get('id').find('//')+2:]
                                        contents.append(f'<{agent_name}>{agent_id}</{agent_name}>')
                                else:
                                    contents.append(f"<{nfo_key}>{item}</{nfo_key}>")

                            if (items := metadata.findall(plex_key)):
                                if nfo_key == "ratings":
                                    ratings = ""
                                    for item in items:
                                        ratings += f'<{item.get("type")}>{item.get("value")}</{item.get("type")}>'
                                    contents.append(f"<ratings>\n{ratings}</ratings>")
                                elif nfo_key == "uniquid":
                                    for item in items:
                                        id = item.get("id")
                                        for id_type in ["imdb", "tmbd", "tvdb"]:
                                            if id_type in id:
                                                contents.append(f'<uniqueid type="{id_type}">{id[id.rfind("/")+1:]}</uniqueid>')
                                                break
                                else:
                                    attributes = []
                                    for item in items:
                                        if nfo_key in ["directors", "writers", "roles"]:
                                            for attribute in ["thumb", "role"]:
                                                if item.get(attribute):
                                                    attributes.append(f"{attribute}=\"{item.get(attribute)}\"")

                                        if nfo_key == "roles":
                                            nfo_key = "actor"

                                        contents.append(f"<{nfo_key}{' ' + " ".join(attributes) if len(attributes) > 0 else ''}>{item.get('tag')}</{nfo_key}>")

                    nfo_written = self._write_nfo(media_type, nfo_path, contents)

                    if media_type != "episode":
                        self._export_poster(metadata, base_path)
                        self._export_fanart(metadata, base_path)

                    if nfo_written:
                        self.logger.info(f"[SUCCESS] {media_type.title()} NFO for {metadata.get('title')} successfully saved to {nfo_path}")
                    else:
                        self.logger.debug(f"[NOCHANGE] {media_type.title()} NFO for {metadata.get('title')} has not changed since last export")
                else:
                    self.logger.debug(f"[SKIPPED] {media_type.title()} NFO for {metadata.get('title')} skipped because existing NFO file is age locked")
            except Exception as e:
                self.logger.error(f"[FAILURE] Failed to write {media_type} NFO for {metadata.get('title')} due to {e}")
                raise e

    def finalize(self) -> None:
        self.registry.save()

    def _export_poster(self, metadata, base_path: Path) -> None:
        if self.config["export_poster"]:
            poster_path = base_path / Path("poster.jpg")
            self._write_image("thumb", metadata, poster_path)

    def _export_fanart(self, metadata, base_path: Path) -> None:
        if self.config['export_fanart']:
            fanart_path = base_path / Path("fanart.jpg")
            self._write_image("art", metadata, fanart_path)

    def _write_nfo(self, nfo_type: str, nfo_path: Path, contents: List[str]) -> None:
        root_element = self._get_nfo_root_element(nfo_type)

        content = "".join([
            '<?xml version="1.0" encoding="UTF-8"?>\n',
            f'<{root_element} xsi="http://www.w3.org/2001/XMLSchema-instance" xsd="http://www.w3.org/2001/XMLSchema">\n  ',
            "\n  ".join(contents),
            f"\n</{root_element}>"
        ])

        return self.registry.write(nfo_path, content)

    def _get_parent_file(self, original_path: Path) -> Path:
        parent_dir = original_path.parent
        new_parent_dir = parent_dir.parent
        new_path = new_parent_dir / original_path.name

        return new_path if os.path.exists(new_path) else None
    
    def _is_same_image(self, image: Image.Image, image_path: Path, check_parent: bool=False) -> bool:
        if check_parent:
            image_path = self._get_parent_file(image_path)

        if image_path and image_path.exists():
            image_bytes_io = io.BytesIO()
            image.save(image_bytes_io, format="jpeg")
            image_bytes = image_bytes_io.getvalue()

            with open(image_path, 'rb') as file:
                file_content = file.read()

            return image_bytes == file_content
        else:
            return False
    
    def _write_image(self, image_type: str, metadata, image_path: Path) -> None:
        try:
            if not self.age_checker.is_locked(image_path):
                image = self.plex.get_image(image_type, metadata)
                if image:
                    if self._is_same_image(image, image_path):
                        self.logger.debug(f"[NOCHANGE] {image_type} for {metadata.get('title')} is has not changed since last export")
                    elif self._is_same_image(image, image_path, True):
                        self.logger.debug(f"[SKIPPED] {image_type} for {metadata.get('title')} is same as parent")
                    else:
                        self.registry.write(image_path, image)
                        self.logger.info(f"[SUCCESS] {image_type} for {metadata.get('title')} successfully saved to {image_path}")
                else:
                    self.logger.debug(f"[SKIPPED] {image_type} for {metadata.get('title')} does not exist")
            else:
                self.logger.debug(f"[SKIPPED] {image_type} for {metadata.get('title')} skipped because existing image is age locked")
        except Exception as e:
            self.logger.info(f"[FAILURE] {image_type} failed to download due to {e}")
            raise e
    
    def _get_nfo_name(self, metadata, media_type: str) -> Path:
        if media_type == "episode":
            episode_path = metadata.find("Media").find("Part").get("file")
            episode_file = os.path.basename(episode_path)
            return Path(f"{episode_file[:episode_file.rfind('.')]}.nfo")
        else:
            return Path(f"{media_type}.nfo")
    
    def _get_nfo_root_element(self, media_type) -> str:
        return self.config["nfo_root_element_mappings"].get(media_type, media_type)
    
    def _get_plex_key(self, nfo_key: str, media_type: str):
        mappings = {
            **self.config["key_mappings"]["global"],
            **{
                "season": self.config["key_mappings"]["season"] or {},
                "episode": self.config["key_mappings"]["episode"] or (),
            }.get(media_type, {})
        }

        return mappings.get(nfo_key, nfo_key)

    def _get_media_keys(self, media_type: str) -> Dict:
        return self.config["media_keys"].get(media_type, {}) or {}
    