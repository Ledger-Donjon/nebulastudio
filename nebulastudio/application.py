from PyQt6.QtWidgets import QApplication, QFileDialog
import os
import yaml
from nebulastudio.nebulastudio import NebulaStudio


class NebulaStudioApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.windows: list[NebulaStudio] = []
        self.setApplicationName("Nebula Studio")
        # self.setApplicationVersion("0.1")
        self.setOrganizationName("Ledger Donjon")
        # self.setOrganizationDomain("nebulastudio.org")
        self.setQuitOnLastWindowClosed(True)

        self.settings_path = None

        try:
            self.load_file("nebulaconfig.yaml")
        except FileNotFoundError:
            print("Configuration file not found, loading default settings.")
            raise
        except ValueError as e:
            print(f"Error loading configuration file: {e}")

        try:
            self.load_file("nebulasettings.yaml")
        except FileNotFoundError:
            print("Settings file not found, loading default settings.")
        except ValueError as e:
            print(f"Error loading settings file: {e}")

    def new_window(self):
        # Create a new instance of NebulaStudio and show it
        window = NebulaStudio()
        self.windows.append(window)
        window.show()

        # Set the new window as the active window
        self.setActiveWindow(window)
        return window

    def load_file(self, path: str):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File {path} does not exist")
        if not path.endswith(".yaml"):
            raise ValueError(f"File {path} is not a YAML file")
        if "settings" in path:
            self.load_settings(path)
        elif "config" in path:
            self.load_config(path)

    def load_config(self, config: str, window: "NebulaStudio | None" = None):
        # Load the settings from a YAML file
        with open(config, "r") as f:
            _config = yaml.safe_load(f)
            if not isinstance(_config, list):
                _config = [_config]

            for i in range(len(_config)):
                win = self.new_window()
                win.load_config(_config[i])

    def load_settings(self, settings: str, window: "NebulaStudio | None" = None):
        # Load the settings from a YAML file
        with open(settings, "r") as f:
            _settings = yaml.safe_load(f)
            if not isinstance(_settings, list):
                _settings = [_settings]

            for win_setting in _settings:
                if "title" in win_setting:
                    title = win_setting["title"]
                    for win in self.windows:
                        if win.windowTitle() == title:
                            win.load_settings(win_setting)
                            break

    @property
    def settings(self) -> list[dict]:
        """
        Returns the settings of the application.
        """
        return [win.settings for win in self.windows]

    def save_settings(self, path: str | None = None):
        """
        Save the settings of the application to a YAML file.
        """
        if path is None:
            # ask the user for a file path
            path, _ = QFileDialog.getSaveFileName(
                None, "Save Settings", "nebulasettings.yaml", "YAML Files (*.yaml)"
            )
            if not path:
                return  # User canceled the dialog

        with open(path, "w") as f:
            yaml.dump(self.settings, f, default_flow_style=False)
