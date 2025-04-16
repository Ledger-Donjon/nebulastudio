from PyQt6.QtCore import Qt, QLocale
from PyQt6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QIcon,
    QColorConstants,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QApplication,
    QWidget,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QWIDGETSIZE_MAX,
)

from .viewer import Viewer
from PyQt6.QtGui import QKeySequence, QGuiApplication
import os
import yaml


class NebulaStudioApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Nebula Studio")
        # self.setApplicationVersion("0.1")
        self.setOrganizationName("Ledger Donjon")
        # self.setOrganizationDomain("nebulastudio.org")
        self.setQuitOnLastWindowClosed(True)
        self.load_path("import.yaml")

    def new_window(self):
        # Create a new instance of NebulaStudio and show it
        window = NebulaStudio()
        window.show()

        # Set the new window as the active window
        self.setActiveWindow(window)

        return window

    def load_path(self, path: str, window: "NebulaStudio | None" = None):
        # Load the settings from a YAML file
        with open(path, "r") as f:
            list_settings = yaml.safe_load(f)
            if not isinstance(list_settings, list):
                list_settings = [list_settings]

            for i in range(len(list_settings)):
                win = self.new_window()
                win.load_settings(list_settings[i])


class NebulaStudio(QMainWindow):
    RETICULA_COLORS: list[QColor | Qt.GlobalColor | int] = [
        QColorConstants.Red,
        QColorConstants.Green,
        QColorConstants.Blue,
        QColorConstants.Yellow,
        QColorConstants.Cyan,
        QColorConstants.Magenta,
    ]

    def __init__(self, settings: dict | None = None):
        super().__init__()
        app = QApplication.instance()
        assert type(app) is NebulaStudioApplication, (
            "NebulaStudio must be created after QApplication"
        )
        self.app = app

        self.setWindowTitle(app.applicationName())
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon("icon.png"))
        self.setLocale(QLocale.system())

        # Set up the main layout
        self.setCentralWidget(w := QWidget())
        w.setLayout(hbox := QHBoxLayout())
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        hbox.addStretch()
        hbox.addLayout(vbox := QVBoxLayout())
        hbox.addStretch()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        vbox.addStretch()
        self.viewers_widget = QWidget()
        vbox.addWidget(self.viewers_widget)
        vbox.addStretch()

        # Set up the horizontal layout for the viewers
        w.setContentsMargins(0, 0, 0, 0)
        self.size_fixed = False
        self.viewers_layout = QGridLayout()
        self.viewers_layout.setContentsMargins(0, 0, 0, 0)
        self.viewers_layout.setSpacing(0)
        self.viewers_widget.setLayout(self.viewers_layout)

        # Set the initial reticula color index
        self.current_reticula_color_index = 0
        self.current_reticula_opacity = 0.4

        # Track internally the number of rows and columns
        self.rows = 0
        self.columns = 0

        # List of viewers
        self.viewers: list[Viewer] = []
        self.new_viewer()

        assert self.rows == 1
        assert self.columns == 1

        # Hide the mouse pointer
        QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)

        self.setAcceptDrops(True)

        # Create a menu
        menu = self.menuBar()
        assert menu is not None
        file_menu = menu.addMenu("&File")
        assert file_menu is not None
        file_menu.addAction("&New Window", QKeySequence("Ctrl+N"), app.new_window)
        file_menu.addAction("&Close Window", QKeySequence("Ctrl+W"), self.close)

        viewers_menu = menu.addMenu("&Viewers")
        assert viewers_menu is not None
        viewers_menu.addAction(
            "&Add Viewer Line",
            QKeySequence("Shift+A"),
            lambda: self.add_viewer_line(True),
        )
        viewers_menu.addAction(
            "&Remove Viewer Line",
            QKeySequence("Shift+R"),
            lambda: self.remove_viewer_line(True),
        )
        viewers_menu.addAction(
            "&Add Viewer Column", QKeySequence("A"), lambda: self.add_viewer_line(False)
        )
        viewers_menu.addAction(
            "&Remove Viewer Column",
            QKeySequence("R"),
            lambda: self.remove_viewer_line(False),
        )

        reticula_menu = menu.addMenu("&Reticula")
        assert reticula_menu is not None
        reticula_menu.addAction(
            "&Change Color", QKeySequence("C"), self.change_reticula_color
        )
        reticula_menu.addAction("&Fix Reticula", QKeySequence("F"), self.fix_reticula)
        reticula_menu.addAction(
            "Change Opaci&ty", QKeySequence("T"), self.change_reticula_opacity
        )
        reticula_menu.addAction(
            "&Show/Hide Mouse Pointer", QKeySequence("S"), self.show_hide_cursor
        )
        reticula_menu.addAction("&Delete Closest Reticula", QKeySequence("D"))

        zoom_menu = menu.addMenu("&Zoom")
        assert zoom_menu is not None
        zoom_menu.addAction(
            "Zoom &In", QKeySequence("Ctrl++"), lambda: self.zoom_viewers(1.2)
        )
        zoom_menu.addAction(
            "Zoom &Out", QKeySequence("Ctrl+-"), lambda: self.zoom_viewers(0.8)
        )
        zoom_menu.addAction(
            "&Reset Zoom", QKeySequence("Ctrl+0"), lambda: self.set_zoom_viewers(1.0)
        )
        zoom_menu.addAction(
            "&Apply Stitch Zoom",
            QKeySequence("Ctrl+Shift+Z"),
            self.apply_stitch_zoom,
        )

        self.stitching: dict | None = None

        if settings is not None:
            self.load_settings(settings)

    def zoom_viewers(self, factor: float):
        # Zoom all viewers
        for v in self.viewers:
            v.zoom(factor)

    def set_zoom_viewers(self, factor: float = 1.0):
        # Set zoom factor for all viewers
        for v in self.viewers:
            v.set_zoom(factor)

    def apply_stitch_zoom(self):
        if self.stitching is None:
            return
        """
            displacements_um: { "x": 172.57, "y": 179.81 }
            pixel_size_in_um: { "x": 14.8305, "y": 14.8305 }
            objective: 20.0
        """
        if self.size_fixed:
            self.viewers_widget.setFixedSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
            self.size_fixed = False
            return

        displacements_um = self.stitching.get("displacements_um")
        pixel_size_in_um = self.stitching.get("pixel_size_in_um")
        objective = self.stitching.get("objective", 1.0)
        if displacements_um is None or pixel_size_in_um is None:
            print("Stitching settings not found")
            return
        assert (
            isinstance(displacements_um, dict)
            and "x" in displacements_um
            and "y" in displacements_um
        )
        assert (
            isinstance(pixel_size_in_um, dict)
            and "x" in pixel_size_in_um
            and "y" in pixel_size_in_um
        )
        assert isinstance(objective, (int, float))

        # Get the size of displacement in pixels
        viewrect_w = objective * displacements_um["x"] / pixel_size_in_um["x"]
        viewrect_h = objective * displacements_um["y"] / pixel_size_in_um["y"]
        # Set the zoom factor for all viewers
        container = self.viewers_widget
        assert container is not None
        # The container of the images must have a size proportional to:
        container_w = viewrect_w * self.columns
        container_h = viewrect_h * self.rows
        # Eg a width/height ratio:
        ratio = container_w / container_h
        # get the current height of the container
        height = container.height()
        container.setFixedSize(
            int(height * ratio),
            int(height),
        )

        self.size_fixed = True

        # The wiewers must shows a portion of the image of height 'viewrect_h'
        # Its actual size is 'height'
        # To show the same portion of image, we need to set the zoom factor
        zoom_factor = (height / self.rows) / viewrect_h

        for viewer in self.viewers:
            viewer.setSceneRect
            viewer.set_zoom(zoom_factor)

    def dragEnterEvent(self, a0: QDragEnterEvent | None) -> None:
        super().dragEnterEvent(a0)
        if a0 is None:
            return
        try:
            mime = a0.mimeData()
            assert mime is not None
            assert mime.hasUrls()
            # Check if the first URL is a valid file path
            url = mime.urls()[0]
            assert url.isLocalFile()
            path = url.toLocalFile()
            assert path is not None
            # Check if the file exists
            if not os.path.isfile(path):
                raise FileNotFoundError(f"File {path} does not exist")
            # Check if the file is a valid image

            yaml.load(open(path), Loader=yaml.SafeLoader)
        except (AssertionError, FileNotFoundError, Exception) as e:
            print(str(e))
            a0.ignore()
            return
        a0.accept()

    def dragMoveEvent(self, a0: QDragMoveEvent | None) -> None:
        return super().dragMoveEvent(a0)

    def dropEvent(self, a0: QDropEvent | None) -> None:
        assert a0 is not None
        mime = a0.mimeData()
        assert mime is not None
        assert mime.hasUrls()
        url = mime.urls()[0]
        assert url.isLocalFile()
        path = url.toLocalFile()
        assert path is not None
        self.app.load_path(path)
        return super().dropEvent(a0)

    def viewer_at(self, row, column) -> Viewer:
        item = self.viewers_layout.itemAtPosition(row, column)
        if item is not None and type(viewer := item.widget()) is Viewer:
            return viewer
        return self.new_viewer(row=row, column=column)

    def load_settings(self, settings: dict):
        if "title" in settings:
            self.setWindowTitle(settings["title"])
            print(f"Window title set to {settings['title']}")

        stitching = settings.get("stitching")
        if stitching is not None:
            assert isinstance(stitching, dict), "'stitching' key must be a dictionary"
        self.stitching = stitching

        images_dict = settings.get("images", {})
        assert isinstance(images_dict, dict), "'images' key must be a dictionary"
        ranges = images_dict.get("ranges", {})
        assert isinstance(ranges, dict), "'ranges' key must be a dictionary"

        def to_range(range_key: str | None, ranges: dict):
            if (
                not isinstance(ranges, dict)
                or range_key is None
                or range_key not in ranges
            ):
                return range(0, 1)

            _list = ranges[range_key]
            if (
                isinstance(_list, list)
                and len(_list) <= 3
                and all(isinstance(i, int) for i in _list)
            ):
                return range(*_list)

            if isinstance(_list, dict):
                if "start" not in _list and "stop" in _list:
                    return range(_list["stop"])
                return range(
                    _list.get("start", 0), _list.get("stop", 0), _list.get("step", 1)
                )

            if isinstance(_list, list):
                return enumerate(_list)

            return range(0, 1)

        row_key = images_dict.get("row_key")
        column_key = images_dict.get("column_key")

        row_range = to_range(images_dict.get("row_key"), ranges)
        column_range = to_range(images_dict.get("column_key"), ranges)

        patterns = images_dict.get("patterns")
        opacities = images_dict.get("opacities")
        if patterns is None or len(patterns) == 0:
            return

        r = 0
        for row in row_range:
            c = 0
            for column in column_range:
                replace = True
                w = self.viewer_at(r, c)
                substitutions = {}
                if row_key is not None:
                    substitutions[row_key] = row if isinstance(row, int) else row[1]
                if column_key is not None:
                    substitutions[column_key] = (
                        column if isinstance(column, int) else column[1]
                    )

                for i, pattern in enumerate(patterns):
                    assert isinstance(pattern, str)
                    filepath = pattern.format(**substitutions)
                    opacity = None
                    if type(opacities) is list and 0 <= i < len(opacities):
                        opacity = opacities[i]
                        if not isinstance(opacity, float):
                            opacity = None
                    w.open_image(filepath, replace=replace, opacity=opacity)
                    replace = False
                c += 1
            r += 1

    def add_viewer_line(self, new_row: bool = True):
        # Add a new viewer to the layout)
        if new_row:
            # Add a new row of viewers
            r_range = range(self.rows, self.rows + 1)
            c_range = range(self.columns)
            self.rows += 1
        else:
            r_range = range(self.rows)
            c_range = range(self.columns, self.columns + 1)
            self.columns += 1
        for r in r_range:
            for c in c_range:
                self.new_viewer(row=r, column=c)

    def remove_viewer_line(self, delete_row: bool = True):
        # Remove a line of viewers from the layout
        if delete_row:
            if self.rows == 1:
                return
            # Remove the last row of viewers
            r_range = range(self.rows - 1, self.rows)
            c_range = range(self.columns)
            self.viewers_layout.setRowStretch(self.rows - 1, 0)
            self.rows -= 1
        else:
            if self.columns == 1:
                return
            r_range = range(self.rows)
            c_range = range(self.columns - 1, self.columns)
            self.viewers_layout.setColumnStretch(self.columns - 1, 0)
            self.columns -= 1
        for r in r_range:
            for c in c_range:
                item = self.viewers_layout.itemAtPosition(r, c)
                if item is not None and type(viewer := item.widget()) is Viewer:
                    self.viewers_layout.removeItem(item)
                    self.viewers.remove(viewer)
                    viewer.deleteLater()

    def show_hide_cursor(self):
        if QGuiApplication.overrideCursor() is None:
            QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
        else:
            QGuiApplication.restoreOverrideCursor()

    def change_reticula_opacity(self):
        self.current_reticula_opacity += 0.1
        self.current_reticula_opacity %= 1.0
        for viewer in self.viewers:
            viewer.set_reticula_opacity(self.current_reticula_opacity)

    def fix_reticula(self):
        for viewer in self.viewers:
            viewer.fix_reticula()

    def delete_closest_reticula(self):
        for viewer in self.viewers:
            viewer.delete_closest_reticula()

    def change_reticula_color(self):
        # Calculate the index of the next color
        self.current_reticula_color_index = (
            self.current_reticula_color_index + 1
        ) % len(self.RETICULA_COLORS)
        # Change the color of the reticula in all viewers
        for viewer in self.viewers:
            viewer.set_reticula_color(
                self.RETICULA_COLORS[self.current_reticula_color_index]
            )

    def new_viewer(
        self, path: str | None = None, row: int = 0, column: int = 0
    ) -> Viewer:
        viewer = Viewer(self)
        self.viewers.append(viewer)
        if path is not None:
            viewer.open_image(path)
        self.viewers_layout.addWidget(viewer, row, column)
        self.viewers_layout.setColumnStretch(column, 1)
        self.viewers_layout.setRowStretch(row, 1)
        viewer.scroll_content_to.connect(self.scroll_all_viewers_to)
        viewer.reticula_pos.connect(self.new_reticula_pos)
        viewer.set_reticula_opacity(self.current_reticula_opacity)

        self.rows = max(self.rows, row + 1)
        self.columns = max(self.columns, column + 1)

        return viewer

    def scroll_all_viewers_to(self, x: int, y: int):
        for viewer in self.viewers:
            viewer.do_scroll_to(x, y)
            # viewer.repaint()

    def new_reticula_pos(self, x, y):
        for viewer in self.viewers:
            viewer.set_reticula_pos(x, y)
