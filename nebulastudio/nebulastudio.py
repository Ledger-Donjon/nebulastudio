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
)
from .viewer import Viewer
from PyQt6.QtGui import QKeySequence, QShortcut, QGuiApplication


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

        # Set up the horizontal layout for the viewers
        self.viewers_layout = QHBoxLayout()
        vbox.addLayout(self.viewers_layout)

        # Accepting drops of images from the file system
        self.setAcceptDrops(True)

        # Set the initial reticula color index
        self.current_reticula_color_index = 0
        self.current_reticula_opacity = 1.0

        # List of viewers
        self.viewers: list[Viewer] = []
        self.new_viewer()

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

    def new_viewer(self, path: str | None = None) -> None:
        viewer = Viewer(self)
        self.viewers.append(viewer)
        if path is not None:
            viewer.open_image(path)
        self.viewers_layout.addWidget(viewer, stretch=1)
        viewer.scroll_by.connect(self.new_scroll_pos)
        viewer.reticula_pos.connect(self.new_reticula_pos)

    def dragEnterEvent(self, a0: QDragEnterEvent | None) -> None:
        assert a0 is not None
        mime = a0.mimeData()
        assert mime is not None
        print("Drag", mime.hasUrls(), mime.hasText(), mime.text())
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

    def new_scroll_pos(self, dx, dy):
        pass

    def new_reticula_pos(self, x, y):
        for viewer in self.viewers:
            viewer.set_reticula_pos(x, y)
