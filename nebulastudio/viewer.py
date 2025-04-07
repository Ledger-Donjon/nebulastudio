from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsLineItem,
)
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtCore import Qt, pyqtSignal, QLineF
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nebulastudio.nebulastudio import NebulaStudio


class Viewer(QGraphicsView):
    scroll_content_to = pyqtSignal(int, int)
    reticula_pos = pyqtSignal(float, float)

    def __init__(self, nebula_studio: "NebulaStudio"):
        super().__init__()

        self.nebula_studio = nebula_studio

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        hscrollbar = self.horizontalScrollBar()
        vscrollbar = self.verticalScrollBar()
        assert hscrollbar is not None and vscrollbar is not None
        self.hscrollbar = hscrollbar
        self.vscrollbar = vscrollbar

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.image_item: QGraphicsPixmapItem | None = None

        hline = self._scene.addLine(0, 0, 0, 0)
        vline = self._scene.addLine(0, 0, 0, 0)
        assert hline is not None and vline is not None

        self.vline = vline
        self.hline = hline
        self.hline.setPen(
            nebula_studio.RETICULA_COLORS[nebula_studio.current_reticula_color_index]
        )
        self.hline.setZValue(1000)
        self.vline.setPen(
            nebula_studio.RETICULA_COLORS[nebula_studio.current_reticula_color_index]
        )
        self.vline.setZValue(1000)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        self.fixed_reticulas: list[tuple[QGraphicsLineItem, QGraphicsLineItem]] = []

        hscrollbar.valueChanged.connect(
            lambda value: self.scroll_content_to.emit(value, vscrollbar.value())
        )
        vscrollbar.valueChanged.connect(
            lambda value: self.scroll_content_to.emit(hscrollbar.value(), value)
        )

    def fix_reticula(self):
        hline = self._scene.addLine(QLineF(self.hline.line()), self.hline.pen())
        vline = self._scene.addLine(QLineF(self.vline.line()), self.vline.pen())
        assert hline is not None and vline is not None
        hline.setZValue(1000)
        vline.setZValue(1000)
        # Set the opacity of the lines to the same as the original reticula
        hline.setOpacity(self.hline.opacity())
        vline.setOpacity(self.vline.opacity())
        self.fixed_reticulas.append((hline, vline))

    def delete_closest_reticula(self):
        closest: int = -1
        min_dist: float = 1e10
        for i, (hline, vline) in enumerate(self.fixed_reticulas):
            dist = (hline.line().x1() - self.hline.line().x1()) ** 2 + (
                hline.line().y1() - self.hline.line().y1()
            ) ** 2
            if dist < min_dist:
                min_dist = dist
                closest = i
        if closest == -1:
            return
        # Remove the closest reticula
        hline, vline = self.fixed_reticulas.pop(closest)
        # Remove the lines from the scene
        self._scene.removeItem(hline)
        self._scene.removeItem(vline)

    def set_reticula_color(self, color: QColor | Qt.GlobalColor | int):
        self.hline.setPen(color)
        self.vline.setPen(color)

    def open_image(self, filename: str):
        if not filename:
            return
        if self.image_item is not None:
            self._scene.removeItem(self.image_item)
        self.image_item = QGraphicsPixmapItem(QPixmap(filename))
        self._scene.addItem(self.image_item)

    def set_reticula_pos(self, x: float, y: float):
        if self.image_item is not None:
            # Get size of the image item
            size = self.image_item.pixmap().size()
            width, height = size.width(), size.height()
            # Calculate the position of the reticula
            x = int(x * width)
            y = int(y * height)
            # Set the position of the reticula
            self.hline.setLine(x, 0, x, height)
            self.vline.setLine(0, y, width, y)

    def set_reticula_opacity(self, opacity: float):
        if self.hline is not None and self.vline is not None:
            self.hline.setOpacity(opacity)
            self.vline.setOpacity(opacity)
        for hline, vline in self.fixed_reticulas:
            if hline is not None and vline is not None:
                hline.setOpacity(opacity)
                vline.setOpacity(opacity)

    def mouseMoveEvent(self, event):
        if event is not None and self.image_item is not None:
            # Get size of the image item
            size = self.image_item.pixmap().size()
            width, height = size.width(), size.height()
            pos = event.pos()
            scene_pos = self.mapToScene(pos)
            x = max(min(width, scene_pos.x()), 0) / width
            y = max(min(height, scene_pos.y()), 0) / height
            self.reticula_pos.emit(x, y)

        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        assert event is not None
        mime = event.mimeData()
        assert mime is not None
        if mime.hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        assert event is not None
        event.accept()

    def dropEvent(self, event):
        assert event is not None
        mime = event.mimeData()
        assert mime is not None
        # Accept the event if it contains URLs
        if mime.hasUrls():
            # Get the first URL from the mime data
            url = mime.urls()[0]
            # Convert the URL to a local file path
            filename = url.toLocalFile()
            # Open the image file
            self.open_image(filename)
            event.accept()
        else:
            event.ignore()

    def do_scroll_to(self, x: int, y: int) -> None:
        self.hscrollbar.setValue(x)
        self.vscrollbar.setValue(y)
