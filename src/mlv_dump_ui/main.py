import logging
import os
import subprocess
import sys

from flet import app, alignment, margin, ThemeMode, icons, ScrollMode
from flet.app_bar import AppBar
from flet.card import Card
from flet.column import Column
from flet.container import Container
from flet.file_picker import FilePicker, FilePickerFileType, FilePickerResultEvent
from flet.filled_tonal_button import FilledTonalButton
from flet.floating_action_button import FloatingActionButton
from flet.icon_button import IconButton
from flet.list_tile import ListTile
from flet.page import Page
from flet.popup_menu_button import PopupMenuButton, PopupMenuItem
from flet.radio import Radio
from flet.radio_group import RadioGroup
from flet.ref import Ref
from flet.row import Row
from flet.text import Text
from flet.textfield import TextField

try:
    from mlv_dump_ui.config import UserConfig
    from mlv_dump_ui.dialogs import ExportDialog, NoImportsDialog, MlvDumpVersionDialog, NoOutputDirDialog
except ModuleNotFoundError:
    sys.path.append(os.path.join(os.getcwd(), "src"))
    from mlv_dump_ui.config import UserConfig
    from mlv_dump_ui.dialogs import ExportDialog, NoImportsDialog, MlvDumpVersionDialog, NoOutputDirDialog


class DeleteButton(IconButton):
    def __init__(self, parent, list_tile: ListTile):
        super().__init__()
        self.list_tile = list_tile
        self.icon = icons.DELETE
        self.on_click = lambda _: parent.delete_from_list(list_tile=self.list_tile)


# Current open Flet issue: https://github.com/flet-dev/flet/issues/884
class MlvDumpUiMain:
    """The main Flet handler for MLV Dump UI.
    """
    title: str = "MLV Dump UI"
    page: Page
    last_picked_dir: str

    def __init__(self, root_path: str):
        self.root_path = root_path
        self.mlv_dump_version = ""
        self.executable = None
        self.dark_mode_view = Ref[PopupMenuItem]()
        self.light_mode_view = Ref[PopupMenuItem]()
        self.imported_list = Ref[Column]()
        self.list_container = Ref[Container]()
        self.output_directory = Ref[TextField]()
        self.output_controls = Ref[Container]()
        self.output_type_selector = Ref[RadioGroup]()
        self.config = UserConfig(root_path=root_path)
        self.save_directory_picker = FilePicker(on_result=self.update_output_directory)
        self.import_files_picker = FilePicker(on_result=self.add_files)
        self.logger = logging.getLogger("MLVDumpUI")

    def render(self) -> None:
        self.page.appbar = AppBar(
            toolbar_height=40,
            actions=[
                PopupMenuButton(
                    content=Container(
                        content=Text("File"),
                        margin=margin.all(10),
                        alignment=alignment.center,
                    ),
                    items=[
                        PopupMenuItem(
                            text="Import",
                            on_click=self.import_files
                        ),
                        PopupMenuItem(
                            text="Export",
                            on_click=self.export
                        ),
                        PopupMenuItem(),
                        PopupMenuItem(
                            text="Exit",
                            on_click=self.exit
                        )
                    ]
                ),
                PopupMenuButton(
                    content=Container(
                        content=Text("View"),
                        margin=margin.all(10),
                        alignment=alignment.center,
                    ),
                    items=[
                        PopupMenuItem(
                            ref=self.dark_mode_view,
                            text="Dark Mode",
                            on_click=lambda _: self.switch_theme(theme_mode=ThemeMode.DARK)
                        ),
                        PopupMenuItem(
                            ref=self.light_mode_view,
                            text="Light Mode",
                            on_click=lambda _: self.switch_theme(theme_mode=ThemeMode.LIGHT)
                        )
                    ]
                ),
                PopupMenuButton(
                    content=Container(
                        content=Text("Info"),
                        margin=margin.all(10),
                        alignment=alignment.center,
                    ),
                    items=[
                        PopupMenuItem(
                            text="About MLV Dump",
                            on_click=self.mlv_dump_version_info
                        )
                    ]
                ),
                Container(
                    expand=True,
                    margin=margin.all(2000),
                    content=Text(""),
                )
            ]
        )
        self.page.floating_action_button = FloatingActionButton(
            content=Text("Export"),
            tooltip="Export using settings",
            on_click=self.export
        )
        self.page.add(
            Column(
                controls=[
                    Card(
                        content=Column(
                            controls=[
                                Row(
                                    controls=[
                                        Container(
                                            margin=margin.symmetric(horizontal=5),
                                            content=FilledTonalButton(
                                                text="Select",
                                                icon=icons.SEARCH,
                                                tooltip="Select output directory",
                                                on_click=self.select_output_directory
                                            )
                                        ),
                                        TextField(
                                            ref=self.output_directory,
                                            label="Output Directory",
                                            disabled=True,
                                            expand=True,
                                            value=self.config.output_directory
                                        )
                                    ]
                                ),
                                Row(
                                    controls=[
                                        Container(
                                            margin=margin.symmetric(horizontal=10),
                                            content=Text("Output Type: ")
                                        ),
                                        RadioGroup(
                                            ref=self.output_type_selector,
                                            value="dng",
                                            on_change=self.update_output_config,
                                            content=Row(
                                                controls=[
                                                    Radio(
                                                        value="dng",
                                                        label="*.dng",
                                                        tooltip="Output frames into separate *.dng files"
                                                    ),
                                                    Radio(
                                                        value="raw",
                                                        label="*.raw",
                                                        tooltip="Output into a legacy *.raw file"
                                                    )
                                                ]
                                            )
                                        ),
                                    ]
                                ),
                                Container(
                                    ref=self.output_controls
                                ),

                            ]
                        )
                    ),
                    Container(
                        ref=self.list_container,
                        height=self.page.height - 250,
                        content=Card(
                            content=Column(
                                controls=[
                                    Column(
                                        expand=True,
                                        ref=self.imported_list,
                                        auto_scroll=True,
                                        scroll=ScrollMode.AUTO,
                                        controls=[]
                                    ),
                                    Container(
                                        margin=margin.all(10),
                                        content=Row(
                                            controls=[
                                                FilledTonalButton(
                                                    icon=icons.FILE_OPEN,
                                                    text="Import",
                                                    tooltip="Import *.MLV files to convert",
                                                    on_click=self.import_files
                                                ),
                                                FilledTonalButton(
                                                    icon=icons.CLEAR,
                                                    text="Clear",
                                                    tooltip="Remove all files from list",
                                                    on_click=self.clear_imported_files
                                                )
                                            ]
                                        )
                                    )
                                ]
                            )
                        )
                    )
                ]
            )
        )
        # Set output config
        self.update_output_config(self.config.output_type if self.config.output_type else "dng")
        # Set Theme
        if self.config.theme:
            self.page.theme_mode = self.config.theme
            if self.config.theme == ThemeMode.DARK.value:
                self.dark_mode_view.current.checked = True
            else:
                self.light_mode_view.current.checked = True

        self.page.update()

    @property
    def dng_controls(self) -> Column:
        return Column(
            controls=[
                Row(
                    controls=[
                        Container(
                            margin=margin.symmetric(horizontal=10),
                            content=Text("Chroma Smoothing: ")
                        ),
                        RadioGroup(
                            value=self.config.chroma_smoothing,
                            on_change=self.update_chroma_smoothing,
                            content=Row(
                                controls=[
                                    Radio(
                                        value=None,
                                        label="None"
                                    ),
                                    Radio(
                                        value="2x2",
                                        label="2x2"
                                    ),
                                    Radio(
                                        value="3x3",
                                        label="3x3"
                                    ),
                                    Radio(
                                        value="5x5",
                                        label="5x5"
                                    )

                                ]
                            )
                        )
                    ]
                )
            ]
        )

    def update_output_config(self, event) -> None:
        output_type = event
        if not isinstance(event, str):
            output_type = output_type.data
        if output_type == "dng":
            self.output_controls.current.content = self.dng_controls
        elif output_type == "raw":
            self.output_controls.current.content = Column()
        self.output_controls.current.update()

    def mlv_dump_version_info(self, _) -> None:
        self.page.dialog = MlvDumpVersionDialog(
            mlv_dump_version=self.mlv_dump_version
        )
        self.page.update()

    def export(self, _) -> None:
        if not self.imported_list.current.controls:
            self.page.dialog = NoImportsDialog()
            self.page.update()
        elif not self.output_directory.current.value:
            self.page.dialog = NoOutputDirDialog()
            self.page.update()
        else:
            exporter = ExportDialog(
                files_to_process=[item for item in self.imported_list.current.controls if isinstance(item, ListTile)],
                root_path=self.root_path,
                executable=self.executable,
                config=self.config,
                logger=self.logger
            )
            self.page.dialog = exporter
            self.page.update()
            exporter.start()

    def clear_imported_files(self, _) -> None:
        self.imported_list.current.controls.clear()
        self.imported_list.current.update()

    def update_dng(self, event) -> None:
        self.config.dng_output = event.control.value

    def update_chroma_smoothing(self, event) -> None:
        self.config.chroma_smoothing = event.control.value

    def switch_theme(self, theme_mode: ThemeMode) -> None:
        self.dark_mode_view.current.checked = False
        self.light_mode_view.current.checked = False
        if theme_mode == ThemeMode.DARK:
            self.dark_mode_view.current.checked = True
        else:
            self.light_mode_view.current.checked = True

        self.config.theme = theme_mode
        self.page.theme_mode = theme_mode
        self.page.update()

    def exit(self, _) -> None:
        self.logger.info("Saving config")
        self.config.save()
        self.page.window_close()

    def add_files(self, event: FilePickerResultEvent) -> None:
        if event.files:
            for file in event.files:
                # Update config if different
                import_dir = os.path.dirname(file.path)
                if self.config.last_import_directory != import_dir:
                    self.config.last_import_directory = import_dir

                # Add to list
                video_tile = ListTile(
                    title=Text(value=file.name),
                    subtitle=Text(value=file.path)
                )
                video_tile.leading = DeleteButton(
                    parent=self,
                    list_tile=video_tile
                )
                self.imported_list.current.controls.insert(0, video_tile)
            # Update view
            self.imported_list.current.update()

    def update_output_directory(self, event: FilePickerResultEvent) -> None:
        if event.path:
            self.output_directory.current.value = event.path
            self.config.output_directory = event.path
            self.output_directory.current.update()

    def import_files(self, _) -> None:
        self.import_files_picker.pick_files(
            dialog_title="Import MLV files to convert",
            allowed_extensions=["MLV", "mlv"],
            file_type=FilePickerFileType.CUSTOM,
            allow_multiple=True,
            initial_directory=self.config.last_import_directory
        )

    def select_output_directory(self, _) -> None:
        self.save_directory_picker.get_directory_path(
            dialog_title="Select Output Directory",
            initial_directory=self.config.output_directory
        )

    def on_page_resize(self, _) -> None:
        self.list_container.current.height = self.page.height - 250
        self.list_container.current.update()

    def delete_from_list(self, list_tile: ListTile) -> None:
        self.imported_list.current.controls.remove(list_tile)
        self.imported_list.current.update()

    def set_executable(self) -> str:
        if self.page.platform == "windows":
            return os.path.join(self.root_path, "bin", "mlv_dump.exe")
        elif self.page.platform == "macos":
            return os.path.join(self.root_path, "bin", "mlv_dump.osx")
        else:
            return os.path.join(self.root_path, "bin", "mlv_dump.linux")

    def get_mlv_dump_version(self) -> str:
        output = subprocess.check_output(
            [os.path.join(self.root_path, "bin", self.executable), "--version"]
        ).decode()
        return output.replace("\r", "")

    def run(self, page: Page) -> None:
        self.page = page
        self.page.title = self.title
        self.executable = self.set_executable()

        self.page.overlay.extend([self.save_directory_picker, self.import_files_picker])

        self.page.on_resize = self.on_page_resize
        self.page.on_disconnect = self.exit

        self.mlv_dump_version = self.get_mlv_dump_version()

        self.logger.info(f"Platform: {self.page.platform}")
        self.logger.info(f"Utilizing executable: {self.executable}")

        self.render()


def main() -> None:
    # make 'logs' dir if it doesn't exist
    root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    user_dir = os.path.join(os.path.expanduser("~"), ".mlv_dump")
    os.makedirs(user_dir, exist_ok=True)
    log_file = os.path.join(user_dir, "mlv_dump_ui.log")
    if os.path.exists(log_file):
        os.remove(log_file)

    logging.basicConfig(
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler(
                filename=log_file
            )
        ]
    )
    app(target=MlvDumpUiMain(root_path=root_path).run)


if __name__ == "__main__":
    main()
