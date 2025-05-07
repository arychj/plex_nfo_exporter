from config import Config
from exporter import Exporter
from logger import Logger
from plex import Plex

def main():
    config = Config.load_config("./config.yml")

    logger = Logger.get_logger(config)

    plex = Plex(
        plex_url=config["baseurl"], 
        token=config["token"], 
        tls_verify=config["tls_verify"],
        logger=logger
    )

    exporter = Exporter(
        config=config,
        plex=plex,
        logger=logger
    )

    libraries = plex.get_libraries(config["library_names"])
    for library in libraries:
        media_type, media_key, medias = plex.get_media(library)
        for media in medias:
            media_metadata = plex.get_metadata(media, media_key)[0]
            if media_metadata.get("title") != "The Agency":
                continue

            exporter.export(media_metadata, media_type)

            if (media_type == "tvshow") and (config["export_season_nfo"] or config["export_episode_nfo"]):
                try:
                    seasons = plex.get_seasons(media)
                    for season in seasons:
                        try:
                            season_metadata = plex.get_metadata(season, "Directory")[0]
                            
                            if config["export_season_nfo"]:
                                exporter.export(season_metadata, "season")

                            if config["export_episode_nfo"]:
                                try:
                                    episodes = plex.get_episodes(season_metadata)
                                    for episode_item in episodes:
                                        episode_metadata = plex.get_metadata(episode_item, 'Video')[0]
                                        exporter.export(episode_metadata, "episode")
                                except Exception as e:
                                    logger.error(f"[FAILURE] Failed to write episode NFO for {media_metadata.get("title")}/{season.get("title")}/{episode_metadata.get("title")} due to {e}")
                        except Exception as e:
                            logger.error(f"[FAILURE] Failed to write season NFO for {media_metadata.get("title")}/{season.get("title")} due to {e}")
                except Exception as e:
                    logger.error(f"[FAILURE] Failed to write episodic NFO for {media_metadata.get("title")} due to {e}")

if __name__ == "__main__":
    main()
