from PyQt6.QtCore import Qt, QLocale
from PyQt6.QtGui import (
    QColor,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QIcon,
    QColorConstants,
    QKeyEvent,
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
from .nebulaimage import NebulaImageGroup
from .toolbars import NebulaStudioToolbar
import os
import yaml
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .application import NebulaStudioApplication


class NebulaStudio(QMainWindow):
    RETICULA_COLORS: list[QColor | Qt.GlobalColor | int] = [
        QColorConstants.Red,
        QColorConstants.Green,
        QColorConstants.Blue,
        QColorConstants.Yellow,
        QColorConstants.Cyan,
        QColorConstants.Magenta,
    ]

    def __init__(self):
        super().__init__()
        app = QApplication.instance()
        assert app is not None, "NebulaStudio must be created after QApplication"
        self.app = cast("NebulaStudioApplication", app)

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

        # Scenarios
        self.scenarios: dict[str, NebulaImageGroup] = {}

        # Track internally the number of rows and columns
        self.rows = 0
        self.columns = 0

        # List of viewers
        self.viewers: list[Viewer] = []
        self.new_viewer()

        assert self.rows == 1
        assert self.columns == 1

        self.setAcceptDrops(True)

        # Create a menu
        menu = self.menuBar()
        assert menu is not None
        file_menu = menu.addMenu("&File")
        assert file_menu is not None
        file_menu.addAction("&New Window", QKeySequence("Ctrl+N"), self.app.new_window)
        file_menu.addAction("&Close Window", QKeySequence("Ctrl+W"), self.close)
        file_menu.addAction(
            "&Save", QKeySequence("Ctrl+S"), lambda: self.app.save_settings()
        )

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
        viewers_menu.addAction(
            "&Refresh Images",
            QKeySequence("Ctrl+R"),
            self.refresh_viewers,
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
            "Toggle Reticula Visibility",
            QKeySequence("Shift+T"),
            self.toggle_reticula_visibility,
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

        # Create a toolbar to adjust images properties
        self.image_prop_toolbar = NebulaStudioToolbar(self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.image_prop_toolbar)
        self.image_prop_toolbar.setAllowedAreas(
            Qt.ToolBarArea.LeftToolBarArea | Qt.ToolBarArea.RightToolBarArea
        )
        # Permit to detach the toolbar
        self.image_prop_toolbar.setMovable(True)
        self.image_prop_toolbar.setFloatable(True)

        self.image_prop_toolbar.update_image_selector()

    def refresh_viewers(self):
        # Refresh all viewers
        for v in self.viewers:
            v.refresh()

    def zoom_viewers(self, factor: float):
        # Zoom all viewers
        for v in self.viewers:
            v.zoom(factor)

    def set_zoom_viewers(self, factor: float = 1.0):
        # Set zoom factor for all viewers
        for v in self.viewers:
            v.set_zoom(factor)

    @property
    def displacement_size_pixels(self) -> tuple[int, int] | None:
        if self.stitching is None:
            return None
        displacements_um = self.stitching.get("displacements_um")
        pixel_size_in_um = self.stitching.get("pixel_size_in_um")
        objective = self.stitching.get("objective", 1.0)
        if displacements_um is None or pixel_size_in_um is None:
            print("Stitching settings not found")
            return None
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

        return (
            int(viewrect_w),
            int(viewrect_h),
        )

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

        # Get the size of displacement in pixels
        displacements = self.displacement_size_pixels
        assert displacements is not None
        viewrect_w, viewrect_h = displacements

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

        # The viewers must shows a portion of the image of height 'viewrect_h'
        # Its actual size is 'height'
        # To show the same portion of image, we need to set the zoom factor
        zoom_factor = (height / self.rows) / viewrect_h

        for viewer in self.viewers:
            # viewer.setSceneRect
            viewer.set_zoom(zoom_factor)
            viewer.refresh()

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
        self.app.load_config(path)
        return super().dropEvent(a0)

    def viewer_at(self, row: int, column: int, create: bool = True) -> Viewer | None:
        item = self.viewers_layout.itemAtPosition(row, column)
        if item is not None and type(viewer := item.widget()) is Viewer:
            return viewer
        if not create:
            return None
        return self.new_viewer(row=row, column=column)

    @property
    def title(self) -> str:
        return self.windowTitle()

    @title.setter
    def title(self, value: str):
        self.setWindowTitle(value)
        self.image_prop_toolbar.setWindowTitle(value + " - Image Parameters")
        print(f"Window title set to {value}")

    def load_config(self, settings: dict):
        if "title" in settings:
            self.title = settings["title"]

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

        scenarios = images_dict.get("scenarios")
        assert type(scenarios) is list, "'scenarios' key must be a list"
        if scenarios is None or len(scenarios) == 0:
            return

        r = 0
        w = None
        for row in row_range:
            c = 0
            for column in column_range:
                replace = True
                w = self.viewer_at(r, c)
                assert w is not None
                substitutions = {}
                if row_key is not None:
                    substitutions[row_key] = row if isinstance(row, int) else row[1]
                if column_key is not None:
                    substitutions[column_key] = (
                        column if isinstance(column, int) else column[1]
                    )

                for i, scenario in enumerate(scenarios):
                    assert isinstance(scenario, dict), (
                        "'scenarios' must be a list of dictionaries"
                    )
                    name = scenario.get("name")
                    assert isinstance(name, str), (
                        "'name' key in scenario must be a string"
                    )
                    pattern = scenario.get("pattern")
                    assert isinstance(pattern, str), (
                        "'pattern' key in scenario must be a string"
                    )
                    filepath = pattern.format(**substitutions)

                    ref_pattern = scenario.get("reference")
                    if ref_pattern is not None:
                        assert isinstance(ref_pattern, str), (
                            "'reference' key in scenario must be a string"
                        )
                        ref_filepath = ref_pattern.format(**substitutions)
                    else:
                        ref_filepath = None

                    if name not in self.scenarios:
                        group = NebulaImageGroup(
                            name, pattern=pattern, reference_pattern=ref_pattern
                        )
                        self.scenarios[name] = group
                    else:
                        group = self.scenarios[name]

                    image = w.open_image(
                        filepath,
                        replace=replace,
                        pattern=pattern,
                        reference=ref_filepath,
                        reference_pattern=ref_pattern,
                    )
                    if image is not None:
                        group.images.append(image)

                    replace = False
                c += 1
            r += 1

        self.image_prop_toolbar.update_image_selector()

    def load_settings(self, settings: dict):
        if "title" in settings and not self.windowTitle() == settings["title"]:
            # Prevent application of settings if the title does not match
            # the current window title
            # This is useful to avoid applying settings to the wrong window
            print(
                f"Window title does not match: {self.windowTitle()} != {settings['title']}"
            )

        # Load scenarios settings
        scenarios = settings.get("scenarios", dict())
        if not isinstance(scenarios, dict):
            print("'scenarios' key must be a dictionary")
        else:
            for scenario, scenario_settings in scenarios.items():
                if scenario not in self.scenarios:
                    print(f"Scenario {scenario} not found in the current window")
                    continue
                self.scenarios[scenario].settings = scenario_settings

        images = settings.get("images", dict())
        if not isinstance(images, dict):
            print("'images' key must be a dictionary")
        else:
            for image_url, image_settings in images.items():
                for viewer in self.viewers:
                    for image in viewer.group.images:
                        if image_url in image.image_url:
                            # Apply the settings to the image
                            image.settings = image_settings

        positions = settings.get("positions", [])
        if not isinstance(positions, list):
            print("'positions' key must be a list")
        else:
            for pos in positions:
                if not isinstance(pos, dict):
                    print("Each position must be a dictionary")
                    continue
                row = pos.get("position", [0, 0])
                if not isinstance(row, list) or len(row) != 2:
                    print("Position must be a list of two integers")
                    continue
                r, c = row
                if not isinstance(r, int) or not isinstance(c, int):
                    print("Row and column must be integers")
                    continue
                viewer = self.viewer_at(r, c)
                assert viewer is not None
                viewer.settings = pos

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

    def toggle_reticula_visibility(self):
        for viewer in self.viewers:
            viewer.toggle_reticula_visibility()

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
        viewer = Viewer(row, column, self)
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

    # When the window becomes active, update the reticula color
    def activateWindow(self) -> None:
        print(f"Activating NebulaStudio window {self.windowTitle()}")
        return super().activateWindow()

    @property
    def settings(self) -> dict:
        """
        Returns the settings of the Nebula Studio window.
        """
        d: dict = {"title": self.windowTitle()}
        positions: list[dict] = []
        for v in self.viewers:
            if (s := v.settings) is not None:
                positions.append(s)
        if positions:
            d["positions"] = positions
        scenarios = {
            scenario.name: s
            for scenario in self.scenarios.values()
            if (s := scenario.settings) is not None
        }
        if scenarios:
            d["scenarios"] = scenarios

        images = {}
        for viewer in self.viewers:
            for img in viewer.group.images:
                if s := img.settings:
                    images[img.name] = s
        if images:
            d["images"] = images
        return d

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            return super().keyPressEvent(a0)
        if a0.key() == Qt.Key.Key_Escape:
            # If Escape is pressed, close the window
            self.close()
            return super().keyPressEvent(a0)

        if a0.key() == Qt.Key.Key_0:
            for scenario in self.scenarios.values():
                for image in scenario.images:
                    image.setVisible(True)

        # Check for key press is 1, 2, 3, 4, 5, 6, 7, 8, or 9
        if a0.key() not in (
            Qt.Key.Key_1,
            Qt.Key.Key_2,
            Qt.Key.Key_3,
            Qt.Key.Key_4,
            Qt.Key.Key_5,
            Qt.Key.Key_6,
            Qt.Key.Key_7,
            Qt.Key.Key_8,
            Qt.Key.Key_9,
        ):
            return super().keyPressEvent(a0)
        index = a0.key() - Qt.Key.Key_1
        if index >= len(self.scenarios):
            return super().keyPressEvent(a0)

        for i, scenario in enumerate(self.scenarios.values()):
            if i != index:
                continue
            visible = scenario.images[0].isVisible() if scenario.images else False
            for image in scenario.images:
                image.setVisible(not visible)

        return super().keyPressEvent(a0)
