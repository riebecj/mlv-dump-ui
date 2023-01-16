import configparser
import os
from typing import Union

from flet import ThemeMode


class UserConfig:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.config_file_path = os.path.join(os.path.expanduser("~"), ".mlv_dump", "mlv_dump_config.ini")
        self.__config = None

    def save(self) -> None:
        with open(self.config_file_path, "wt", encoding="utf8") as config:
            self.config.write(config)

    @property
    def config(self) -> configparser.ConfigParser:
        if not self.__config:
            self.__config = configparser.ConfigParser()
            if os.path.exists(self.config_file_path):
                self.__config.read(self.config_file_path)
            else:
                self.__config["DEFAULT"] = {
                    "theme": "",
                    "output_directory": "",
                    "import_directory": "",
                    "output_type": "dng",
                    "chroma_smoothing": ""
                }
        return self.__config

    @property
    def theme(self) -> str:
        return self.config.get(
            section="DEFAULT",
            option="theme",
        )

    @theme.setter
    def theme(self, value: Union[ThemeMode, str]) -> None:
        if isinstance(value, ThemeMode):
            value = value.value
        self.config.set(
            section="DEFAULT",
            option="theme",
            value=value
        )

    @property
    def output_directory(self) -> str:
        return self.config.get(
            section="DEFAULT",
            option="output_directory",
            fallback=""
        )

    @output_directory.setter
    def output_directory(self, value: str) -> None:
        self.config.set(
            section="DEFAULT",
            option="output_directory",
            value=value
        )

    @property
    def last_import_directory(self) -> str:
        return self.config.get(
            section="DEFAULT",
            option="import_directory",
            fallback=""
        )

    @last_import_directory.setter
    def last_import_directory(self, value: str) -> None:
        self.config.set(
            section="DEFAULT",
            option="import_directory",
            value=value
        )

    @property
    def output_type(self) -> str:
        return self.config.get(
            section="DEFAULT",
            option="output_type",
            fallback=False
        )

    @output_type.setter
    def output_type(self, value: str) -> None:
        self.config.set(
            section="DEFAULT",
            option="output_type",
            value=value
        )

    @property
    def chroma_smoothing(self) -> str:
        return self.config.get(
            section="DEFAULT",
            option="chroma_smoothing",
            fallback=""
        )

    @chroma_smoothing.setter
    def chroma_smoothing(self, value: str) -> None:
        self.config.set(
            section="DEFAULT",
            option="chroma_smoothing",
            value=value
        )

    def __repr__(self) -> str:
        settings = ", ".join(
            [f"{prop}={value if value else None}" for prop, value in self.config["DEFAULT"].items()]
        )
        return f"UserConfig({settings})"
