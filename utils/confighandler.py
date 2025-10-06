import os
import yaml

class AppProperties:
    def __init__(self, filepath):
        self.filepath = filepath
        self.yaml_conf = None
        self._load()

    def _load(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"App properties file missing: {self.filepath}")
        with open(self.filepath, "r") as file:
            self.yaml_conf = yaml.safe_load(file) or {}

    def get(self, key_path, default=None):
        """
        Get a value from the YAML using dot-separated keys.
        Example: get("database.host")
        """
        keys = key_path.split(".")
        value = self.yaml_conf
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path, value):
        """
        Set a value in the YAML using dot-separated keys.
        Creates nested dicts if they don't exist.
        Example: set("database.host", "127.0.0.1")
        """
        keys = key_path.split(".")
        d = self.yaml_conf
        for key in keys[:-1]:
            if key not in d or not isinstance(d[key], dict):
                d[key] = {}
            d = d[key]
        d[keys[-1]] = value

    def save(self):
        """Write changes back to the YAML file"""
        with open(self.filepath, "w") as file:
            yaml.safe_dump(self.yaml_conf, file, default_flow_style=False)
