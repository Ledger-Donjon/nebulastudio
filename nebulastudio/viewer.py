from PyQt6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsLineItem,
    QFrame,
)
from .nebulaimage import NebulaImage, NebulaImageGroup
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, pyqtSignal, QLineF
from typing import TYPE_CHECKING
import os

if TYPE_CHECKING:
    from nebulastudio.nebulastudio import NebulaStudio


class Viewer(QGraphicsView):
    scroll_content_to = pyqtSignal(int, int)
    reticula_pos = pyqtSignal(float, float)

    def __init__(self, row: int, column: int, nebula_studio: "NebulaStudio"):
        super().__init__()

        self.nebula_studio = nebula_studio
        self.row, self.column = (row, column)

        # self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContentsMargins(0, 0, 0, 0)
        self.setFrameShape(QFrame.Shape.NoFrame)

        hscrollbar = self.horizontalScrollBar()
        vscrollbar = self.verticalScrollBar()
        assert hscrollbar is not None and vscrollbar is not None
        self.hscrollbar = hscrollbar
        self.vscrollbar = vscrollbar

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.group = NebulaImageGroup(f"Row {row}, Column {column}")

        hline = self._scene.addLine(0, 0, 0, 0)
        vline = self._scene.addLine(0, 0, 0, 0)
        assert hline is not None and vline is not None

        hline.setVisible(False)
        vline.setVisible(False)

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

        self.setAcceptDrops(True)

        self.sizePolicy().setHeightForWidth(True)

        self.setContentsMargins(0, 0, 0, 0)

    @property
    def image_item(self) -> QGraphicsPixmapItem | None:
        if self.group.images:
            return self.group.images[-1]
        return None

    def set_image_opacity(self, index: int, opacity: float):
        """
        Set the opacity of the image at the given index.
        If the index is out of bounds, do nothing.
        """
        if 0 <= index < len(self.group.images):
            self.group.images[index].setOpacity(opacity)
            print(f"Set opacity of image {index} to {opacity}")
        else:
            print(f"Index {index} out of bounds for images list")

    def open_image(
        self,
        filename: str,
        replace: bool = False,
        pattern: str | None = None,
        reference: None | str = None,
        reference_pattern: str | None = None,
    ):
        try:
            image = NebulaImage(
                filename,
                reference_url=reference,
                pattern=pattern,
                reference_pattern=reference_pattern,
            )

        except Exception as e:
            print("Failed to create image from file:", filename, e)
            return

        if replace:
            # Remove all image items from the scene
            for image in self.group.images:
                self._scene.removeItem(image)
            self.group.images.clear()

        self.group.images.append(image)
        self._scene.addItem(image)
        print("Image item added to scene:", filename, len(self.group.images))
        return image

    def set_reticula_pos(self, x: float, y: float):
        visible = self.hline.isVisible()
        if not visible:
            return
        has_image = (image := self.image_item) is not None
        if has_image:
            # Get size of the image item
            size = image.pixmap().size()
            width, height = size.width(), size.height()
            # Calculate the position of the reticula
            x = int(x * width)
            y = int(y * height)
            # Set the position of the reticula
            self.hline.setLine(x, 0, x, height)
            self.vline.setLine(0, y, width, y)

        self.hline.setVisible(has_image)
        self.vline.setVisible(has_image)

    def toggle_reticula_visibility(self):
        """
        Toggle the visibility of the reticula.
        If the reticula are visible, hide them.
        If they are hidden, show them.
        """
        if self.hline is not None and self.vline is not None:
            visible = self.hline.isVisible()
            self.hline.setVisible(not visible)
            self.vline.setVisible(not visible)
            for hline, vline in self.fixed_reticulas:
                if hline is not None and vline is not None:
                    hline.setVisible(not visible)
                    vline.setVisible(not visible)

    def set_reticula_opacity(self, opacity: float):
        if self.hline is not None and self.vline is not None:
            self.hline.setOpacity(opacity)
            self.vline.setOpacity(opacity)
        for hline, vline in self.fixed_reticulas:
            if hline is not None and vline is not None:
                hline.setOpacity(opacity)
                vline.setOpacity(opacity)

    def fix_reticula(self):
        """
        Create a static reticula at the current position of the reticula
            and add it to the list of fixed reticulas.
        """
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
        """
        Delete the closest fixed reticula from the current position of the reticula.
        """
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
        """
        Change the color of the reticula.

        :param color: The color of the reticula to apply.
        """
        self.hline.setPen(color)
        self.vline.setPen(color)

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events to update the reticula position.

        :param event: The mouse move event.
        """
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

    def zoom(self, factor: float):
        # Set the scale of the view
        self.blockSignals(True)
        self.scale(factor, factor)
        self.blockSignals(False)

    def set_zoom(self, factor: float = 1.0):
        # Set the scale of the view
        self.blockSignals(True)
        self.resetTransform()
        self.scale(factor, factor)
        self.blockSignals(False)

    def do_scroll_to(self, x: int, y: int) -> None:
        self.hscrollbar.setValue(x)
        self.vscrollbar.setValue(y)

    def dragEnterEvent(self, event):
        """
        To handle the drad and drop event of image in the viewer.
        This method checks if the dragged item is a valid image file and
        if so, it accepts the event. Otherwise, it ignores the event.
        It modifies the drop action based on the Alt key modifier
        to indicate if the user wants to add images or replace them.

        :param event: The drag enter event.
        """
        super().dragEnterEvent(event)
        if event is None:
            return
        try:
            mime = event.mimeData()
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
            assert path.lower().endswith(
                (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".npy")
            ), f"File {path} is not a valid image"
        except (AssertionError, FileNotFoundError) as e:
            print(str(e))
            event.ignore()
            return

        if Qt.KeyboardModifier.AltModifier in event.modifiers():
            event.setDropAction(Qt.DropAction.CopyAction)
        else:
            event.setDropAction(Qt.DropAction.LinkAction)

        event.accept()

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)
        assert event is not None
        if Qt.KeyboardModifier.AltModifier in event.modifiers():
            event.setDropAction(Qt.DropAction.CopyAction)
        else:
            event.setDropAction(Qt.DropAction.LinkAction)
        event.accept()

    def dropEvent(self, event):
        super().dropEvent(event)
        assert event is not None
        mime = event.mimeData()
        assert mime is not None
        # Accept the event if it contains URLs
        if not mime.hasUrls():
            event.ignore()
            return

        replace = Qt.DropAction.CopyAction in event.proposedAction()
        for url in mime.urls():
            # Check if the URL is a local file
            if not url.isLocalFile():
                continue
            # Convert the URL to a local file path
            filename = url.toLocalFile()
            # Open the image file
            self.open_image(filename, replace=replace)
            replace = False
            event.acceptProposedAction()

    def refresh(self):
        """
        Refresh the viewer by updating the image items.
        This method is called when the user wants to refresh the viewer.
        It updates the image items in the scene.
        """
        for image in self.group.images:
            image.update_pixmap()
        # self.set_zoom(1.0)
        # self.setReticulaPos(0.5, 0.5)

    @property
    def settings(self) -> dict | None:
        """
        Opens the settings dialog for the viewer.
        """
        d = self.group.settings
        if d is None:
            return None
        d["position"] = [self.row, self.column]
        return d

    @settings.setter
    def settings(self, value: dict):
        """
        Sets the settings for the viewer.
        """
        if (
            "position" in value
            and isinstance(value["position"], list)
            and value["position"] == [self.row, self.column]
        ):
            self.group.settings = value
