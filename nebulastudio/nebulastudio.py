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
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QLabel,
    QGridLayout,
)
from .viewer import Viewer
from PyQt6.QtGui import QKeySequence, QShortcut, QGuiApplication


class NebulaStudioApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("Nebula Studio")
        # self.setApplicationVersion("0.1")
        self.setOrganizationName("Ledger Donjon")
        # self.setOrganizationDomain("nebulastudio.org")
        self.setQuitOnLastWindowClosed(True)

        self.new_window()

    def new_window(self):
        # Create a new instance of NebulaStudio and show it
        window = NebulaStudio()
        window.show()

        # Set the new window as the active window
        self.setActiveWindow(window)


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
        assert type(app) is NebulaStudioApplication, (
            "NebulaStudio must be created after QApplication"
        )

        self.setWindowTitle(app.applicationName())
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon("icon.png"))
        self.setLocale(QLocale.system())

        # Shortcut to change the color of the reticula
        QShortcut(QKeySequence("C"), self).activated.connect(self.change_reticula_color)
        QShortcut(QKeySequence("F"), self).activated.connect(self.fix_reticula)
        QShortcut(QKeySequence("D"), self).activated.connect(
            self.delete_closest_reticula
        )
        QShortcut(QKeySequence("T"), self).activated.connect(
            self.change_reticula_opacity
        )
        QShortcut(QKeySequence("S"), self).activated.connect(self.show_hide_cursor)
        QShortcut(QKeySequence("Ctrl+N"), self).activated.connect(app.new_window)
        QShortcut(QKeySequence("A"), self).activated.connect(
            lambda: self.add_viewer_line(False)
        )
        QShortcut(QKeySequence("Shift+A"), self).activated.connect(self.add_viewer_line)
        QShortcut(QKeySequence("R"), self).activated.connect(
            lambda: self.remove_viewer_line(False)
        )
        QShortcut(QKeySequence("Shift+R"), self).activated.connect(
            self.remove_viewer_line
        )

        # Set up the main layout
        self.setCentralWidget(w := QWidget())
        w.setLayout(vbox := QVBoxLayout())

        # Set up the horizontal layout for the shortcuts description
        vbox.addLayout(hbox := QHBoxLayout())
        hbox.addWidget(QLabel("C: Change reticula color"))
        hbox.addWidget(QLabel("F: Fix reticula"))
        hbox.addWidget(QLabel("D: Delete closest reticula"))
        hbox.addWidget(QLabel("T: Change reticula opacity"))
        hbox.addWidget(QLabel("S: Show/Hide mouse pointer"))
        hbox.addStretch()
        vbox.addLayout(hbox := QHBoxLayout())
        hbox.addWidget(QLabel("(Shift+)A: Add column (or row) of viewers"))
        hbox.addWidget(QLabel("(Shift+)R: Remove column (or row) of viewers"))
        hbox.addStretch()

        # Set up the horizontal layout for the viewers
        self.viewers_layout = QGridLayout()
        vbox.addLayout(self.viewers_layout)

        # Accepting drops of images from the file system
        self.setAcceptDrops(True)

        # Set the initial reticula color index
        self.current_reticula_color_index = 0
        self.current_reticula_opacity = 0.4

        # List of viewers
        self.viewers: list[Viewer] = []
        self.new_viewer()

        # Track internally the number of rows and columns
        self.rows = 1
        self.columns = 1

        # Hide the mouse pointer
        QGuiApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)

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
        return viewer

    def dragEnterEvent(self, a0: QDragEnterEvent | None) -> None:
        assert a0 is not None
        mime = a0.mimeData()
        assert mime is not None
        if mime.hasUrls():
            a0.accept()
        else:
            a0.ignore()
        return super().dragEnterEvent(a0)

    def dragMoveEvent(self, a0: QDragMoveEvent | None) -> None:
        return super().dragMoveEvent(a0)

    def dropEvent(self, a0: QDropEvent | None) -> None:
        assert a0 is not None
        mime = a0.mimeData()
        assert mime is not None
        # Accept the event if it contains URLs
        if mime.hasUrls():
            # Get the first URL from the mime data
            url = mime.urls()[0]
            # Convert the URL to a local file path
            filename = url.toLocalFile()
            # Open the image file
            self.new_viewer(filename)
            a0.accept()
        else:
            a0.ignore()
        return super().dropEvent(a0)

    def scroll_all_viewers_to(self, x: int, y: int):
        for viewer in self.viewers:
            viewer.do_scroll_to(x, y)
            # viewer.repaint()

    def new_reticula_pos(self, x, y):
        for viewer in self.viewers:
            viewer.set_reticula_pos(x, y)
