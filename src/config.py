from dotenv import load_dotenv

import os
import re
import yaml

class Config:
    def load_config(config_path: str = "config.yml"):
        load_dotenv()

        yaml.SafeLoader.add_constructor("!env_var", Config.env_var_constructor)

        with open(config_path, "r") as file:
            config_content = file.read()
            config_content = re.sub(r"\$\{(\w+)\}", lambda match: os.getenv(match.group(1), ""), config_content)

            config = yaml.safe_load(config_content)
            config["baseurl"] = f"{config["baseurl"].strip('/')}"

            return config
        
    def env_var_constructor(loader, node):
        value = loader.construct_scalar(node)
        pattern = re.compile(r"\$\{(\w+)\}")
        match = pattern.findall(value)

        for var in match:
            value = value.replace(f"${{{var}}}", os.getenv(var, ""))

        return value
    