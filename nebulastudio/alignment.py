from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt, QPointF, QEvent, QRect
from PyQt6.QtGui import (
    QKeyEvent,
    QCloseEvent,
    QMouseEvent,
    QPixmap,
    QEnterEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QDockWidget,
    QGraphicsView,
    QLabel,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QGraphicsScene,
    QGraphicsPixmapItem,
)
from .nebulaimage import NebulaImage
from .diff import make_rgb_pixmap
import numpy
from .utils.colors import LedgerColors

if TYPE_CHECKING:
    from .nebulastudio import NebulaStudio


class NebulaAlignmentView(QGraphicsView):
    """
    A label for displaying alignment information in Nebula Studio.
    """

    def __init__(self, toolbox: "ImageAlignmentToolbox"):
        """
        Initializes the NebulaAlignmentView instance.
        """
        super().__init__(toolbox)
        self.toolbox = toolbox

        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("background-color: lightgray;")
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
        return self.toolbox.kernel_size

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

        self.setStyleSheet("background-color: lightblue;")
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
        self.toolbox.find_best_alignment(
            kernel_rect=self.alignment_kernel.rect().toRect()
        )


class ImageAlignmentToolbox(QDockWidget):
    """
    A toolbox for aligning images in Nebula Studio.
    """

    def __init__(self, nebula_studio: "NebulaStudio"):
        """
        Initializes the ImageAlignmentToolbox instance.
        """
        super().__init__("Image Alignment Toolbox")
        self.nebula_studio = nebula_studio
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

        self.setWidget(w := QWidget())
        w.setLayout(vbox)

        self.image: NebulaImage | None = None
        self.image_other: NebulaImage | None = None
        self.alignment_score = numpy.inf
        self.direction: Qt.AlignmentFlag | None = None
        self.hide()

        self.topLevelChanged.connect(self.dockWidget_topLevelChanged)

        # Initialize kernel size for alignment in pixels
        self.kernel_size = 10

    def dockWidget_topLevelChanged(self, floating: bool):
        """
        Handles the top-level change event of the dock widget.
        This method is used to set the window flags when the dock widget is floating.
        """
        if floating:
            self.setWindowFlags(
                Qt.WindowType.CustomizeWindowHint
                | Qt.WindowType.Tool
                | Qt.WindowType.WindowMinimizeButtonHint
                | Qt.WindowType.WindowMaximizeButtonHint
                | Qt.WindowType.WindowCloseButtonHint
            )
            self.show()

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        # Detect left right, up down arrow keys
        if a0 is not None and (image := self.image) is not None:
            # Detect if shift is pressed
            if a0.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                diff = 10
            else:
                diff = 1

            if a0.key() == Qt.Key.Key_N:
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
                    print("No next image found in the same scenario.")
                    next_image = curr_image.same_scenario_image(
                        Qt.AlignmentFlag.AlignBottom
                    )
                    if next_image is not None:
                        next_image.align(Qt.AlignmentFlag.AlignTop)

                return super().keyPressEvent(a0)

            # Detect the 'm' key for auto-alignment
            elif a0.key() == Qt.Key.Key_M:
                best_pos = init_pos = image.pos()
                res = image.align()
                if res is None:
                    print("Alignment failed")
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
                return super().keyPressEvent(a0)

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

    def closeEvent(self, event: QCloseEvent | None) -> None:
        if self.image is not None:
            # Reset the image to None when closing the toolbox
            self.image.last_alignment_direction = None
        self.image = None
        self.image_other = None
        self.alignment_score = numpy.inf
        self.direction = None
        self.hide()
        return super().closeEvent(event)

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
            print("Cropping rectangle has zero width or height, cannot crop.")
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
        if a0.angleDelta().y() > 0:
            self.kernel_size += 1
        else:
            if self.kernel_size > 1:
                self.kernel_size -= 1

        for view in (self.l, self.r, self.d, self.s):
            view.update_alignment_kernel()

    def find_best_alignment(self, kernel_rect: QRect | None = None):
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
            print("No images set for alignment.")
            return

        if kernel_rect is None:
            # We use the integrality of the image
            sub_image = self.image.image_to_show
            sub_image_other = self.image_other.image_to_show
        else:
            # We use the kernel rectangle to crop the image
            sub_image = self.image.image[
                kernel_rect.top() : kernel_rect.bottom(),
                kernel_rect.left() : kernel_rect.right(),
            ]
            sub_image_other = self.image_other.image[
                kernel_rect.top() : kernel_rect.bottom(),
                kernel_rect.left() : kernel_rect.right(),
            ]

        print(
            f"Sub-image size: {sub_image.shape}, Sub-image other size: {sub_image_other.shape}"
        )

        label1 = QLabel("Left Image")
        label1.setPixmap(make_rgb_pixmap(sub_image, balances=self.image.balances))
        label2 = QLabel("Right Image")
        label2.setPixmap(
            make_rgb_pixmap(sub_image_other, balances=self.image_other.balances)
        )
        self.res = QWidget()
        res_layout = QVBoxLayout(self.res)
        res_layout.addWidget(label1)
        res_layout.addWidget(label2)
        self.res.show()
