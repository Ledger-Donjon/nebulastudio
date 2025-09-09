from typing import TYPE_CHECKING
import logging
import numpy
from PyQt6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QPointF, QRect, QEvent, QPoint
from PyQt6.QtGui import (
    QColor,
    QKeyEvent,
    QCloseEvent,
    QWheelEvent,
    QPixmap,
    QEnterEvent,
    QMouseEvent,
)

if TYPE_CHECKING:
    from ..nebulastudio import NebulaStudio

from ..nebulaimage import NebulaImage
from ..diff import make_rgb_pixmap

from ..utils.colors import LedgerColors


class NebulaAlignmentView(QGraphicsView):
    """
    A label for displaying alignment information in Nebula Studio.
    """

    def __init__(self, window: "ImageAlignmentWindow"):
        """
        Initializes the NebulaAlignmentView instance.
        """
        super().__init__(window)
        self._window = window

        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scene = QGraphicsScene()
        self.setScene(scene)
        self.pixmap_item = QGraphicsPixmapItem()
        scene.addItem(self.pixmap_item)

        alignment_kernel = scene.addRect(
            0,
            0,
            100,
            100,
            pen=LedgerColors.SafetyOrange.value,
            brush=Qt.GlobalColor.transparent,
        )
        assert alignment_kernel is not None, "Alignment kernel could not be created"
        alignment_kernel.setZValue(1000)  # Ensure it is on top of the pixmap
        alignment_kernel.setVisible(False)  # Initially hidden
        self.alignment_kernel = alignment_kernel

        self.setMouseTracking(True)  # Enable mouse tracking to detect mouse movements

    @property
    def pixmap(self) -> QPixmap:
        """
        Returns the pixmap currently set in the alignment view.
        """
        return self.pixmap_item.pixmap()

    @pixmap.setter
    def pixmap(self, value: QPixmap):
        """
        Sets the pixmap for the alignment view.
        """
        self.pixmap_item.setPixmap(value)
        # Set the scene rectangle to fit the pixmap
        if scene := self.scene():
            scene.setSceneRect(self.pixmap_item.boundingRect())

    @property
    def kernel_size(self) -> int:
        """
        Returns the size of the alignment kernel.
        """
        return self._window.kernel_size

    def update_alignment_kernel(self, position: QPointF | None = None):
        """
        Updates the position of the alignment kernel rectangle based on the mouse position.
        """
        if position is None:
            position = self.alignment_kernel.rect().center()
        self.alignment_kernel.setRect(
            position.x() - self.kernel_size / 2,
            position.y() - self.kernel_size / 2,
            self.kernel_size,
            self.kernel_size,
        )

    def enterEvent(self, event: QEnterEvent | None) -> None:
        """
        Handles the mouse enter event.
        """
        if event is None:
            return super().enterEvent(event)

        position = int(event.position().x()), int(event.position().y())
        position = self.mapToScene(*position)
        self.update_alignment_kernel(position)
        self.alignment_kernel.setVisible(True)
        super().enterEvent(event)

    def mousePressEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return super().mousePressEvent(event)
        # Update the alignment kernel position
        position = self.mapToScene(event.pos())
        self.update_alignment_kernel(position)
        self.alignment_kernel.setVisible(True)
        self.setMouseTracking(True)  # Enable mouse tracking on mouse press
        # Remove cursor
        self.setCursor(Qt.CursorShape.BlankCursor)
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None) -> None:
        if event is None:
            return super().mouseMoveEvent(event)
        # Update the alignment kernel position
        position = self.mapToScene(event.pos())
        self.update_alignment_kernel(position)
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.alignment_kernel.setVisible(True)
        self._window.find_best_alignment(self.alignment_kernel.rect().toRect())
        super().mouseMoveEvent(event)

    def leaveEvent(self, a0: QEvent | None) -> None:
        """
        Handles the mouse leave event.
        """
        if a0 is None:
            return super().leaveEvent(a0)
        # Hide the alignment kernel rectangle
        self.alignment_kernel.setVisible(False)
        # Restore the cursor
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(a0)

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        if event is not None:
            event.ignore()  # Explicitly ignore

    def wheelEvent(self, event: QWheelEvent | None) -> None:
        if event is None:
            return super().wheelEvent(event)

        # Check if shift is pressed
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # If shift is pressed, ignore the wheel event
            event.ignore()
            return
        return super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent | None) -> None:
        if not self.alignment_kernel:
            return super().mouseDoubleClickEvent(event)
        correction_offset = self._window.find_best_alignment(
            kernel_rect=self.alignment_kernel.rect().toRect()
        )
        if correction_offset is not None:
            self._window.image.setPos(self._window.image.pos() - correction_offset)
            self._window.image.align()


class ImageAlignmentResultDockWidget(QDockWidget):
    """
    A dock widget for displaying the result of image alignment.
    """

    def __init__(self):
        super().__init__("Image Alignment Result")
        self.res = QWidget()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.result_images = [
            QLabel("Left Image"),
            QLabel("Right Image"),
            QLabel("Result Image"),
            QLabel("Alignment Score"),
        ]
        res_layout = QVBoxLayout(self.res)
        # Align content horizontally
        res_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        res_layout.setContentsMargins(0, 0, 0, 0)
        for i in range(4):
            hbox = QHBoxLayout()
            hbox.addStretch()
            hbox.addWidget(self.result_images[i])
            hbox.addStretch()
            res_layout.addLayout(hbox)
        self.setWidget(self.res)

    def show_result(
        self,
        pm_1: QPixmap,
        pm_2: QPixmap,
        pm_3: QPixmap,
        best_score: float,
        best_x: int,
        best_y: int,
        correction_offset: QPoint,
    ):
        """
        Shows the result of the image alignment.
        """
        self.result_images[0].setPixmap(pm_1)
        self.result_images[1].setPixmap(pm_2)
        self.result_images[2].setPixmap(pm_3)
        self.result_images[3].setText(
            f"Best score\nat {best_x}, {best_y}\nCorrection offset: {correction_offset.x()}, {correction_offset.y()}"
        )
        self.setToolTip(f"Best score: {best_score}")


class ImageAlignmentWindow(QMainWindow):
    """
    A window for aligning images.
    """

    def __init__(self, nebula_studio: "NebulaStudio"):
        """
        Initializes the ImageAlignmentWindow instance.
        """
        super().__init__(nebula_studio)
        self.nebula_studio = nebula_studio
        self.result_dock_widget = ImageAlignmentResultDockWidget()
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self.result_dock_widget
        )
        self.setWindowTitle("Image Alignment")
        self.setGeometry(100, 100, 800, 600)

        self.l, self.r = NebulaAlignmentView(self), NebulaAlignmentView(self)
        self.d, self.s = NebulaAlignmentView(self), NebulaAlignmentView(self)

        vbox = QVBoxLayout()
        grid = QGridLayout()

        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.addStretch()
        vbox.addLayout(grid)
        vbox.addStretch()

        self.l.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self.r.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.d.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.s.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        grid.addWidget(self.l, 0, 0)
        grid.addWidget(self.r, 0, 1)
        grid.addWidget(self.d, 1, 0)
        grid.addWidget(self.s, 1, 1)
        self.message = QLabel("Result of alignment will be shown here.")
        self.message.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop
        )
        grid.addWidget(self.message, 2, 0, 1, 2)
        grid.setRowStretch(2, 1)

        self.setCentralWidget(w := QWidget())
        w.setLayout(vbox)

        self.image: NebulaImage | None = None
        self.image_other: NebulaImage | None = None
        self.alignment_score = numpy.inf
        self.direction: Qt.AlignmentFlag | None = None

        # Keep a history of previous comparison states for navigation
        self.history: list[tuple[NebulaImage, Qt.AlignmentFlag]] = []
        self.hide()

        # Initialize kernel size for alignment in pixels
        self.kernel_size = 10
        # Store the last cropped arrays currently displayed in the views
        self.cropped_left = None
        self.cropped_right = None

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is not None and (image := self.image) is not None:
            # Detect if shift is pressed
            if a0.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                diff = 10
            else:
                diff = 1

            # Detect the 'n' key for next image
            if a0.key() == Qt.Key.Key_N:
                # Save current state before moving forward
                if self.direction is not None:
                    self.history.append((image, self.direction))
                next_image = image.same_scenario_image(Qt.AlignmentFlag.AlignRight)
                if next_image is not None:
                    next_image.align(Qt.AlignmentFlag.AlignLeft)
                else:
                    # Go to left-most image in the same scenario
                    curr_image = image
                    while (
                        next_image := curr_image.same_scenario_image(
                            Qt.AlignmentFlag.AlignLeft
                        )
                    ) is not None:
                        curr_image = next_image

                    next_image = curr_image.same_scenario_image(
                        Qt.AlignmentFlag.AlignBottom
                    )
                    if next_image is not None:
                        next_image.align(Qt.AlignmentFlag.AlignTop)

            # Detect the 'p' key for previous image alignment
            elif a0.key() == Qt.Key.Key_P:
                if self.history:
                    img, direction = self.history.pop()
                    img.align(direction)

            # Detect the 'm' key for auto-alignment
            elif a0.key() == Qt.Key.Key_M:
                best_pos = init_pos = image.pos()
                res = image.align()
                if res is None:
                    logging.getLogger(__name__).warning("Alignment failed")
                    return super().keyPressEvent(a0)

                for x in range(-self.kernel_size * diff, (self.kernel_size + 1) * diff):
                    for y in range(
                        -self.kernel_size * diff, (self.kernel_size + 1) * diff
                    ):
                        image.setPos(init_pos.x() + x, init_pos.y() + y)
                        score = image.align()
                        if score is not None and score < res:
                            res = score
                            best_pos = image.pos()
                image.setPos(best_pos)
                image.align()

            # Detect the left/right/up/down arrow keys
            elif a0.key() == Qt.Key.Key_Left:
                image.setPos(image.pos().x() - diff, image.pos().y())
                image.align()
            elif a0.key() == Qt.Key.Key_Right:
                image.setPos(image.pos().x() + diff, image.pos().y())
                image.align()
            elif a0.key() == Qt.Key.Key_Up:
                image.setPos(image.pos().x(), image.pos().y() - diff)
                image.align()
            elif a0.key() == Qt.Key.Key_Down:
                image.setPos(image.pos().x(), image.pos().y() + diff)
                image.align()

        return super().keyPressEvent(a0)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        if self.image is not None:
            # Reset the image to None when closing the toolbox
            self.image.last_alignment_direction = None
        self.image = None
        self.image_other = None
        self.alignment_score = numpy.inf
        self.direction = None
        # Reset the history
        self.history = []
        self.hide()
        return super().closeEvent(a0)

    def set_images(
        self, image_left: NebulaImage, image_right: NebulaImage, offset: QPointF
    ):
        self.image = image_left
        self.image_other = image_right
        if (dx := offset.x()) > 0:
            direction = Qt.AlignmentFlag.AlignRight
        elif dx < 0:
            direction = Qt.AlignmentFlag.AlignLeft
        elif offset.y() > 0:
            direction = Qt.AlignmentFlag.AlignBottom
        else:
            direction = Qt.AlignmentFlag.AlignTop
        self.direction = direction

        # Get the image size
        numpy_image_l = image_left.image_to_show
        assert numpy_image_l is not None, "Image data is not available"

        numpy_image_r = image_right.image_to_show
        assert numpy_image_r is not None, "Image data is not available"

        height, width = numpy_image_l.shape[:2]  # Get the height and width of the image
        assert type(height) is int and type(width) is int, (
            f"Image dimensions are not integers: height={height}, width={width}"
        )

        # Compute the cropping rectangle of the image
        cropping_origin = offset

        # Adjust the cropping rectangle to the current offset applied on the current image
        cropping_origin -= image_left.pos()
        cropping_origin += image_right.pos()

        cropping_width = width - abs(x := int(cropping_origin.x()))
        cropping_height = height - abs(y := int(cropping_origin.y()))

        if cropping_width <= 0 or cropping_height <= 0:
            logging.getLogger(__name__).warning(
                "Cropping rectangle has zero width or height, cannot crop."
            )
            return

        cropped_array = numpy_image_l[
            y if y >= 0 else 0 : height if y >= 0 else height + y,
            x if x >= 0 else 0 : width if x >= 0 else width + x,
            :,
        ]
        cropped_pixmap = make_rgb_pixmap(cropped_array, balances=image_left.balances)
        cropped_array2 = numpy_image_r[
            0 if y >= 0 else -y : height - y if y >= 0 else height,
            0 if x >= 0 else -x : width - x if x >= 0 else width,
            :,
        ]
        cropped_pixmap2 = make_rgb_pixmap(cropped_array2, balances=image_right.balances)
        # Cache the cropped arrays for subsequent refinement
        self.cropped_left = cropped_array
        self.cropped_right = cropped_array2
        cropped_diff = abs(
            cropped_array.astype(numpy.int64) - (cropped_array2.astype(numpy.int64))
        ).astype(numpy.uint64)
        cropped_diff_pixmap = make_rgb_pixmap(
            cropped_diff, balances=image_left.balances
        )

        if cropped_array.ndim == 3:
            cropped_array = cropped_array[:, :, 0]
        if cropped_array2.ndim == 3:
            cropped_array2 = cropped_array2[:, :, 0]
        stacked = numpy.stack([cropped_array, cropped_array2, cropped_array], axis=2)
        cropped_sum = stacked.squeeze()
        cropped_sum_pixmap = make_rgb_pixmap(cropped_sum, balances=image_left.balances)

        self.image = image_left

        self.setWindowTitle(
            f"Result of alignment {image_left.name} with {image_right.name}"
        )

        self.l.pixmap = cropped_pixmap
        self.r.pixmap = cropped_pixmap2
        self.s.pixmap = cropped_sum_pixmap
        self.d.pixmap = cropped_diff_pixmap

        self.alignment_score = cropped_diff.sum()
        self.message.setText(
            f"Aligned {image_left.name} with {image_right.name} in direction {direction.name}, score: {self.alignment_score}"
        )

        self.show()

    def wheelEvent(self, a0: QWheelEvent | None) -> None:
        # Handle the wheel event to augment or reduce the kernel size
        if a0 is None:
            return super().wheelEvent(a0)

        # Check if shift is pressed
        if Qt.KeyboardModifier.ShiftModifier not in a0.modifiers():
            # If shift is not pressed, ignore the wheel event
            a0.ignore()
            return

        if a0.angleDelta().y() > 0:
            self.kernel_size += 2
        else:
            if self.kernel_size > 2:
                self.kernel_size -= 2

        # Make kernel size odd
        if self.kernel_size % 2 == 0:
            self.kernel_size += 1

        for view in (self.l, self.r, self.d, self.s):
            view.update_alignment_kernel()

    def find_best_alignment(self, kernel_rect: QRect):
        """
        Finds the best alignment for the images based on the current kernel size.
        """
        if (
            self.image is None
            or self.image_other is None
            or self.image.image_to_show is None
            or self.image_other.image_to_show is None
            or self.image.image is None
            or self.image_other.image is None
        ):
            logging.getLogger(__name__).warning("No images set for alignment.")
            return

        # Use the currently displayed cropped arrays to keep coordinates consistent
        left = (
            self.cropped_left
            if self.cropped_left is not None
            else self.image.image_to_show
        )
        right = (
            self.cropped_right
            if self.cropped_right is not None
            else self.image_other.image_to_show
        )
        if left is None or right is None:
            logging.getLogger(__name__).warning(
                "No image data available for alignment preview."
            )
            return

        # For the left image we extract the size of the kernel rectangle
        h, w = left.shape[:2]
        x0 = max(0, kernel_rect.left())
        y0 = max(0, kernel_rect.top())
        x1 = min(w, kernel_rect.left() + kernel_rect.width())
        y1 = min(h, kernel_rect.top() + kernel_rect.height())

        # The image we will search for the best alignment
        sub_image = left[y0:y1, x0:x1].copy()

        # For the right image we extract the double size of the kernel rectangle
        h, w = right.shape[:2]
        big_kernel_left = kernel_rect.left() - kernel_rect.width() // 2
        big_kernel_top = kernel_rect.top() - kernel_rect.height() // 2
        x0 = max(0, big_kernel_left)
        y0 = max(0, big_kernel_top)
        x1 = min(w, big_kernel_left + 2 * kernel_rect.width())
        y1 = min(h, big_kernel_top + 2 * kernel_rect.height())

        # The image where we will search for the best alignment
        sub_image_other = right[y0:y1, x0:x1].copy()

        logging.getLogger(__name__).info(
            "Sub-image size: %s, Sub-image other size: %s",
            sub_image.shape,
            sub_image_other.shape,
        )
        if sub_image.shape[0] <= 3 or sub_image.shape[1] <= 3:
            logging.getLogger(__name__).warning(
                "Left image is too small to find the best alignment."
            )
            return
        if sub_image_other.shape[0] <= 3 or sub_image_other.shape[1] <= 3:
            logging.getLogger(__name__).warning(
                "Right image is too small to find the best alignment."
            )
            return

        # We try to find the left image (sub_image) in the right image (sub_image_other)
        DX = sub_image_other.shape[0] - sub_image.shape[0]
        DY = sub_image_other.shape[1] - sub_image.shape[1]
        logging.getLogger(__name__).info("DX: %d, DY: %d", DX, DY)
        if DX <= 0 or DY <= 0:
            logging.getLogger(__name__).warning("No space to find the best alignment.")
            return

        best_x = 0
        best_y = 0
        best_score = numpy.inf
        for x in range(DX):
            for y in range(DY):
                sub_image_other_cropped = sub_image_other[
                    x : x + sub_image.shape[0], y : y + sub_image.shape[1]
                ]
                score = numpy.sum(numpy.abs(sub_image - sub_image_other_cropped))
                if score < best_score:
                    best_score = score
                    best_x = x
                    best_y = y

        # Replace in the second (green) channel of sub_image_other the data of sub_image
        sub_image_other_diff = sub_image_other.copy()
        sub_image_other_diff[
            best_x : best_x + sub_image.shape[0],
            best_y : best_y + sub_image.shape[1],
            1,
        ] = sub_image[:, :, 1]

        # Make an outline rectangle
        color: QColor = LedgerColors.SafetyOrange.value
        rgb = [color.red(), color.green(), color.blue()]
        sub_image_other_diff[
            best_x : best_x + sub_image.shape[0],
            best_y : best_y + 1,
        ] = rgb
        sub_image_other_diff[
            best_x : best_x + sub_image.shape[0],
            best_y + sub_image.shape[1] - 1 : best_y + sub_image.shape[1],
        ] = rgb
        sub_image_other_diff[
            best_x : best_x + 1,
            best_y : best_y + sub_image.shape[1],
        ] = rgb
        sub_image_other_diff[
            best_x + sub_image.shape[0] - 1 : best_x + sub_image.shape[0],
            best_y : best_y + sub_image.shape[1],
        ] = rgb

        pm_1 = make_rgb_pixmap(sub_image, balances=self.image.balances)
        pm_2 = make_rgb_pixmap(sub_image_other, balances=self.image_other.balances)
        pm_3 = make_rgb_pixmap(sub_image_other_diff, balances=self.image_other.balances)

        # In term of correction, we need to apply the following offset to the left image
        self.correction_offset = QPoint(
            best_x - (kernel_rect.left() - big_kernel_left),
            best_y - (kernel_rect.top() - big_kernel_top),
        )

        self.result_dock_widget.show_result(
            pm_1, pm_2, pm_3, best_score, best_x, best_y, self.correction_offset
        )

        logging.getLogger(__name__).info(
            "Correction offset: %s", self.correction_offset
        )
        return self.correction_offset
        # self.image.setPos(self.image.pos() - correction_offset)
        # self.image.align()
