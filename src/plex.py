import requests
import urllib3
import xml.etree.ElementTree as ET
from io import BytesIO
from PIL import Image

from typing import List

from logger import Logger

class Plex:
    def __init__(self, plex_url: str, token: str, tls_verify: bool, logger: Logger):
        self.plex_url = plex_url
        self.tls_verify = tls_verify
        self.logger = logger

        self._build_headers(token=token)
        
        urllib3.disable_warnings()

    def get_libraries(self, library_names: List[str]):
        library_details = []

        response = self._make_request("library/sections", "library")
        root = ET.fromstring(response.content)

        for search_library in library_names:
            directories = root.findall("Directory")
            for library in directories:
                if library.attrib.get("title") == search_library:
                    library_details.append({"key": library.attrib.get("key"), "type": library.attrib.get("type")})

        return library_details
    
    def get_media(self, library):
        url = f"library/sections/{library.get("key")}/all"
        response = self._make_request(url, "media")
        media = ET.fromstring(response.content)
        self._debug(media)

        if library.get("type") == "movie":
            media_type = "movie"
            media_key = "Video"
        elif library.get("type") == "show":
            media_type = "tvshow"
            media_key = "Directory"
            
        medias = media.findall(media_key)

        return media_type, media_key, medias

    def get_seasons(self, tvshow):
        seasons = self.get_metadata(tvshow, "Directory", True)
        seasons = self._clean_tree(seasons)
        return seasons
    
    def get_episodes(self, season):
        episodes = self.get_metadata(season, "Video", True)
        episodes = self._clean_tree(episodes)
        return episodes
    
    def get_metadata(self, item, item_key = None, children: bool = False):
        key = item.get("key")
        if not children:
            key = key.rstrip("/children") if key.endswith("/children") else key

        response = self._make_request(key, "metadata")
        metadata = ET.fromstring(response.content)
        self._debug(metadata)
        
        return metadata.findall(item_key) if item_key else metadata
    
    def get_image(self, type, metadata):
        if (key := metadata.get(type)):
            response = self._make_request(key, "type")
            image = Image.open(BytesIO(response.content))
            image = image.convert("RGB")
            return image
        else:
            return None

    def _debug(self, tree):
        self.logger.debug(f"GET: {ET.tostring(tree, 'utf-8').decode('utf-8')}")

    def _clean_tree(self, tree):
        for element in list(tree):
            if element.get("key", "").endswith("allLeaves"):
                tree.remove(element)
        
        return tree

    def _make_request(self, url: str, type: str):
        try:
            url = f"{self.plex_url}/{url.strip('/')}"
            self.logger.debug(f"GET: {url}")

            response = requests.get(url, headers=self.headers, verify=self.tls_verify)
            if response.status_code == 200:
                return response
            else:
                self.logger.error(f"Failed to retrieve {type}. HTTP Status Code: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to retrieve {type} due to {e}")
    
    def _build_headers(self, token: str):
        self.headers = {"X-Plex-Token": token}
