import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from flet import icons, colors
from flet.alert_dialog import AlertDialog
from flet.column import Column
from flet.elevated_button import ElevatedButton
from flet.icon import Icon
from flet.list_tile import ListTile
from flet.progress_ring import ProgressRing
from flet.text import Text
from flet.text_button import TextButton

from mlv_dump_ui.config import UserConfig


class BaseDialog(AlertDialog):
    def __init__(self):
        super().__init__()

    def close(self, _):
        self.open = False
        self.update()


class NoImportsDialog(BaseDialog):
    def __init__(self):
        super().__init__()
        self.content = Text("Import *.MLV files to convert first")
        self.actions = [
            TextButton("Ok", on_click=self.close)
        ]
        self.open = True


class NoOutputDirDialog(BaseDialog):
    def __init__(self):
        super().__init__()
        self.content = Text("Select an output directory first")
        self.actions = [
            TextButton("Ok", on_click=self.close)
        ]
        self.open = True


class MlvDumpVersionDialog(BaseDialog):
    def __init__(self, mlv_dump_version: str):
        super().__init__()
        title, _, last_update, _, build_date = [i.strip() for i in mlv_dump_version.split('\n') if i]
        self.title = Text(title)
        self.content = Column(
            tight=True,
            controls=[
                Text(last_update),
                Text(build_date)
            ]
        )
        self.open = True


class ExportDialog(BaseDialog):
    def __init__(self,
                 files_to_process: List[ListTile],
                 root_path: str,
                 executable: str,
                 config: UserConfig,
                 logger: logging.Logger):
        super().__init__()
        self.root_path = root_path
        self.files_to_process = files_to_process
        self.executable = executable
        self.config = config
        self.logger = logger
        self.title = Text(value="Export MLV Files")
        self.process_list = Column(
            width=500,
            tight=True
        )
        self.content = self.process_list
        self.close_button = ElevatedButton(
            text="Close",
            on_click=self.close,
            disabled=True
        )
        self.actions = [
            self.close_button
        ]
        self.open = True
        self.on_dismiss = self.can_dismiss

    def can_dismiss(self, _) -> None:
        if self.close_button.disabled:
            self.open = True
            self.page.update()

    def __convert(self, name: str, path: str) -> None:
        name = name.replace(".MLV", "")
        command = [
            os.path.join(self.root_path, "bin", self.executable)
        ]
        self.logger.info(self.config)
        if self.config.output_type == "raw":
            self.logger.info(f"Converting {name} into RAW")
            command.extend(["-o", os.path.join(self.config.output_directory, name), "-r"])
        elif self.config.output_type == "dng":
            self.logger.info(f"Converting {name} into DNG")
            output_dir = os.path.join(self.config.output_directory, name)
            os.makedirs(output_dir, exist_ok=False)
            command.extend(["-o", os.path.join(output_dir, name)])
            self.logger.info(f"Made directory: {os.path.join(self.config.output_directory, name)}")
            command.append("--dng")
            if self.config.chroma_smoothing:
                command.append(f"--cs{self.config.chroma_smoothing}")

        startupinfo = subprocess.STARTUPINFO()
        if self.page.platform == "windows":
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # add input file as last arg
        command.append(path)
        self.logger.info(f"Executing command: {command}")
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            startupinfo=startupinfo
        )

    def add_tile_to_list(self, name: str) -> ListTile:
        conversion_process_tile = ListTile(
            title=Text(f"Converting {name} to {self.config.output_type.upper()}"),
            trailing=ProgressRing()
        )
        self.process_list.controls.append(conversion_process_tile)
        self.process_list.update()
        return conversion_process_tile

    def update_tile(self, name: str, tile: ListTile, error: Optional[str] = None) -> None:
        if error:
            self.logger.error(f"{name} Encountered error: {error}")
            tile.trailing = Icon(
                name=icons.ERROR,
                color=colors.RED,
            )
            tile.tooltip = error
        else:
            self.logger.info(f"Converted {name} successfully.")
            tile.trailing = Icon(
                name=icons.CHECK,
                color=colors.GREEN
            )
        tile.update()

    def process(self) -> None:
        threads = []
        with ThreadPoolExecutor() as executor:
            for file in self.files_to_process:
                name = file.title.value  # noqa
                path = file.subtitle.value  # noqa
                tile = self.add_tile_to_list(name=name)
                # self.__convert(name=name, path=path)
                thread = executor.submit(self.__convert, name=name, path=path)
                thread.name = name
                thread.tile = tile
                threads.append(thread)

            for thread in as_completed(threads):
                if thread.exception():
                    self.update_tile(
                        name=thread.name,
                        tile=thread.tile,
                        error=thread.exception().__str__()
                    )
                else:
                    self.update_tile(
                        name=thread.name,
                        tile=thread.tile
                    )

        self.close_button.disabled = False
        self.update()

    def start(self) -> None:
        self.process()
