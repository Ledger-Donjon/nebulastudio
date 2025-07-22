from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneMouseEvent,
    QGraphicsPixmapItem,
    QGraphicsSceneContextMenuEvent,
    QMenu,
)
from PyQt6.QtCore import Qt, QPointF
from PIL import Image
import os
import numpy

from .diff import make_rgb_pixmap, construct_diff_ndarray
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .nebulastudio import NebulaStudio
    from .viewer import Viewer


class NebulaImage(QGraphicsPixmapItem):
    """
    A class representing an image in Nebula Studio.
    """

    def __init__(
        self,
        image_url: str | None = None,
        reference_url: str | None = None,
        pattern: str | None = None,
        reference_pattern: str | None = None,
    ):
        """
        Initializes the NebulaImage instance.

        Args:
            image_url (str): The URL of the image.
            pattern (str): The pattern of filename it is from.
        """
        super().__init__()
        self.image_url = image_url
        self.reference_url = reference_url
        self.pattern = pattern
        self.reference_pattern = reference_pattern

        self.image = None
        self.reference_image = None
        self.average_image = None
        self.diff_image = None
        self._balances = (0.0, 1.0)

        # Used to store the min and max values of the whole scenario for normalization
        self.minmax: tuple[int, int] | None = None

        # Populate image, reference image and diff image objects
        if self.image_url is not None:
            self.load_files(self.image_url, self.reference_url)
        self.update_pixmap()

        self.last_alignment_direction = None

    @property
    def name(self) -> str:
        """
        Returns the URL of the image.
        """
        return os.path.basename(self.image_url) if self.image_url else "Unnamed Image"

    @staticmethod
    def file_to_numpy(filename: str | None) -> numpy.ndarray | None:
        if filename is None:
            return None

        if not (os.path.exists(filename) and os.path.isfile(filename)):
            raise FileNotFoundError(f"File {filename} does not exist")

        if filename.endswith(".npy"):
            # Load the image from the numpy file
            return numpy.load(filename).astype(numpy.uint64)

        image = Image.open(filename)
        # Convert the image in grayscale if the image has only one channel
        if image.mode in ("L", "1", "P"):
            image = image.convert("L")  # Convert to grayscale
        else:
            image = image.convert("RGB")

        return numpy.array(image)

    def load_files(self, filename: str, reference: str | None = None):
        self.image = self.file_to_numpy(filename)
        self.reference_image = self.file_to_numpy(reference)
        if self.image is not None and self.reference_image is not None:
            self.diff_image = construct_diff_ndarray(self.image, self.reference_image)

    def update_tooltip(self):
        self.setToolTip(
            f"Image: {self.name}"
            + (
                f"\nReference: {os.path.basename(self.reference_url)}"
                if self.reference_url
                else ""
            )
            + (f"\nGroup: {self.viewer.group.groupname}" if self.viewer else "")
            + (
                f"\nScenarios: {','.join([scenario.name for scenario in scenarios])}"
                if (scenarios := self.scenarios)
                else ""
            )
        )

    @property
    def image_to_show(self) -> numpy.ndarray | None:
        """
        Returns the image to be displayed, either the diff image or the original image.
        """
        if self.image is None:
            return

        # If the image is not loaded, use the average image if available
        if self.diff_image is not None:
            image_to_show = self.diff_image
        elif self.average_image is not None:
            image_to_show = (
                self.image.astype(numpy.int64) - self.average_image.astype(numpy.int64)
            )
            image_to_show += image_to_show.min()
        else:
            image_to_show = self.image
        return image_to_show

    def update_pixmap(self):
        """
        Updates the pixmap with the numpy image to show.
        """
        if (img := self.image_to_show) is not None:
            self.setPixmap(
                make_rgb_pixmap(
                    img,
                    balances=self.balances,
                )
            )
        else:
            self.setPixmap(QPixmap())  # Clear the pixmap if no image is loaded

    @property
    def balances(self) -> tuple[float, float]:
        """
        Returns the black and white balances of the image.
        """
        return self._balances

    @balances.setter
    def balances(self, value: tuple[float, float]):
        """
        Sets the black and white balances of the image.

        Args:
            value (tuple[float, float]): The new black and white balances.
        """
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError("Balances must be a tuple of two floats.")
        self._balances = value
        self.update_pixmap()

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent | None) -> None:
        print(f"Double clicked on image: {self.name}")
        self.select_in_panel()
        if event is not None:
            event.accept()
        return super().mouseDoubleClickEvent(event)

    def select_in_panel(self):
        """
        Selects the image in the image panel of the Nebula Studio.
        """
        if (ns := self.nebula_studio) is not None:
            ns.image_prop_toolbox.image_panel.image = self
        else:
            print("Nebula Studio instance is not available.")

    # Context menu settings for the image
    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent | None) -> None:
        """Handles the context menu event for the image."""
        if event is not None:
            menu = QMenu()
            menu.addSection(f"{self.name} Alignment")
            menu.addAction("Align left", lambda: self.align(Qt.AlignmentFlag.AlignLeft))
            menu.addAction(
                "Align right", lambda: self.align(Qt.AlignmentFlag.AlignRight)
            )
            menu.addAction("Align top", lambda: self.align(Qt.AlignmentFlag.AlignTop))
            menu.addAction(
                "Align bottom", lambda: self.align(Qt.AlignmentFlag.AlignBottom)
            )
            menu.addAction(
                "Set same offset for all images",
                lambda: self.align(Qt.AlignmentFlag.AlignCenter),
            )
            menu.exec(event.screenPos())
            event.accept()

    def same_scenario_image(self, direction: Qt.AlignmentFlag):
        """
        Finds the image in the same scenario as this one, in the specified direction.
        """
        if (v := self.viewer) is None or (ns := self.nebula_studio) is None:
            print("No viewer found for alignment.")
            return

        if direction == Qt.AlignmentFlag.AlignLeft:
            v2 = ns.viewer_at(v.row, v.column - 1, create=False)
        elif direction == Qt.AlignmentFlag.AlignRight:
            v2 = ns.viewer_at(v.row, v.column + 1, create=False)
        elif direction == Qt.AlignmentFlag.AlignTop:
            v2 = ns.viewer_at(v.row - 1, v.column, create=False)
        elif direction == Qt.AlignmentFlag.AlignBottom:
            v2 = ns.viewer_at(v.row + 1, v.column, create=False)
        else:
            print(f"Unknown alignment direction: {direction}")
            return

        # Get image of the same group in the other viewer
        if v2 is None:
            print(f"No viewer found in direction {direction}.")
            return

        image = None
        for image in v2.group.images:
            if any(s in self.scenarios for s in image.scenarios):
                break

        if image is None:
            return

        return image

    def align(self, direction: Qt.AlignmentFlag | None = None):
        """
        Aligns the image to the left, right, top, or bottom of the viewer.
        This method is a placeholder and should be implemented with actual alignment logic.
        """

        if direction is None:
            direction = self.last_alignment_direction
        if direction is None:
            print("No alignment direction specified.")
            return

        if direction == Qt.AlignmentFlag.AlignCenter:
            for image in self.siblings:
                image.setPos(self.pos())
            return

        self.select_in_panel()
        self.last_alignment_direction = direction

        assert (ns := self.nebula_studio) is not None, (
            "NebulaStudio instance is not available"
        )
        assert (d := ns.displacement_size_pixels) is not None
        dx, dy = d

        image_right = self.same_scenario_image(direction)
        if image_right is None:
            print(f"No image found in the same scenario in direction {direction.name}.")
            return

        if direction == Qt.AlignmentFlag.AlignRight:
            cropping_origin = QPointF(dx, 0)
        elif direction == Qt.AlignmentFlag.AlignLeft:
            cropping_origin = QPointF(-dx, 0)
        elif direction == Qt.AlignmentFlag.AlignTop:
            cropping_origin = QPointF(0, -dy)
        elif direction == Qt.AlignmentFlag.AlignBottom:
            cropping_origin = QPointF(0, dy)
        else:
            cropping_origin = QPointF()

        ns.alignment_toolbox.set_images(self, image_right, cropping_origin)
        return ns.alignment_toolbox.alignment_score

    @property
    def next_viewer_image(self) -> "NebulaImage | None":
        """
        Returns the image in the next viewer.
        """
        if (v := self.viewer) is not None:
            images = v.group.images
            try:
                index = images.index(self)
                return images[index + 1] if index + 1 < len(images) else None
            except ValueError:
                return None
        return None

    @property
    def settings(self) -> dict | None:
        """
        Returns the settings for the image.
        """
        d = {}
        if self.opacity() < 1.0:
            d["opacity"] = self.opacity()
        if ((p := self.pos()).x(), p.y()) != (0.0, 0.0):
            d["offset"] = [p.x(), p.y()]
        if self.balances != (0.0, 1.0):
            d["balances"] = list(self.balances)
        return d if d else None

    @settings.setter
    def settings(self, value: dict):
        """
        Sets the settings for the image.

        Args:
            value (dict): The new settings for the image.
        """
        print(f"Setting image settings: {value} to {self.name}")
        if "opacity" in value:
            self.setOpacity(value["opacity"])
        if "offset" in value:
            self.setPos(QPointF(float(value["offset"][0]), float(value["offset"][1])))
            self.update_pixmap()
        if "balances" in value:
            self.balances = tuple(value["balances"])
            self.update_pixmap()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent | None) -> None:
        if event is not None and event.modifiers() & Qt.KeyboardModifier.AltModifier:
            self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable)
            self.posOrigin = self.pos()
            if (v := self.viewer) is not None:
                for image in v.group.images:
                    image.posOrigin = image.pos()

        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent | None) -> None:
        self.setFlag(QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, False)
        if event is not None and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            diff = self.pos() - self.posOrigin
            for image in self.siblings:
                if image is not self:
                    image.setPos(image.posOrigin + diff)
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent | None) -> None:
        # If MAJ is pressed, we want to move all the images in the group
        if event is not None and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            diff = self.pos() - self.posOrigin
            for image in self.siblings:
                if image is not self:
                    image.setPos(image.posOrigin + diff)

        return super().mouseMoveEvent(event)

    @property
    def viewer(self) -> "Viewer | None":
        """
        Returns the viewer associated with this image.
        """
        if (scene := self.scene()) is not None:
            return cast("Viewer", scene.parent())
        return None

    @property
    def siblings(self) -> list["NebulaImage"]:
        """
        Returns a list of sibling images in the same viewer.
        """
        if (v := self.viewer) is not None:
            return v.group.images
        return []

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change in [
            QGraphicsItem.GraphicsItemChange.ItemVisibleHasChanged,
        ]:
            self.update_tooltip()
        return super().itemChange(change, value)

    @property
    def nebula_studio(self) -> "NebulaStudio | None":
        """
        Returns the NebulaStudio instance associated with this image.
        """
        if (v := self.viewer) is not None:
            return v.nebula_studio
        return None

    @property
    def scenarios(self) -> list["NebulaImageGroup"]:
        """
        Returns a list of scenarios associated with this image.
        """
        if ns := self.nebula_studio:
            return [
                scenario
                for scenario in ns.scenarios.values()
                if scenario.images and self in scenario.images
            ]
        return []


class NebulaImageGroup(NebulaImage):
    """A class that permits to handle parameters for a group of images (eg, from same scenario)."""

    def __init__(
        self,
        groupname: str,
        pattern: str | None = None,
        reference_pattern: str | None = None,
    ):
        super().__init__(
            image_url=None,
            reference_url=None,
            pattern=pattern,
            reference_pattern=reference_pattern,
        )
        self.images: list[NebulaImage] = []
        self.groupname = groupname

    @property
    def name(self) -> str:
        """
        Return the name of the group.
        """
        return self.groupname

    def apply_average(self):
        """
        Applies the average image to all images in the group.
        """
        if self.average_image is not None:
            self.average_image = None
            return

        self.average_image = numpy.median(
            numpy.array([image.image for image in self.images]), axis=0
        ).astype(numpy.uint64)

        if self.average_image is None:
            print("No average image available.")
            return

        _min, _max = (
            self.images[0].image.min(),
            self.images[1].image.max(),
        )
        for image in self.images:
            if image.image is None:
                continue
            _min, _max = (
                min(image.image.min(), _min),
                max(image.image.max(), _max),
            )  # Ensure the image is updated
        # Update the average image for each image in the group

        for image in self.images:
            image.minmax = (_min, _max)
            image.average_image = self.average_image
            image.update_pixmap()
            image.update_tooltip()

    def export_images(self, path: str):
        """
        Stitch all the images of the group into a single image.
        """

        if not os.path.exists(path):
            os.makedirs(path)

        viewer = self.images[0].viewer
        displacement = viewer.nebula_studio.displacement_size_pixels
        # Create a big image.
        big_image = numpy.zeros((
            displacement[0] * viewer.nebula_studio.rows + 1000,
            displacement[1] * viewer.nebula_studio.columns + 1000,
            3   
        ), dtype=numpy.uint8)


        for image in self.images:
            if (im := image.image_to_show) is None:
                continue

            x = int(-image.pos().x() + im.shape[1] / 2 - displacement[0] / 2)
            y = int(-image.pos().y() + im.shape[0] / 2 - displacement[1] / 2)


            y_start = 0 if image.viewer.row == 0 else y
            x_start = 0 if image.viewer.column == 0 else x

            y_end = (y + displacement[1]) if image.viewer.row < viewer.nebula_studio.rows - 1 else im.shape[0]
            x_end = (x + displacement[0]) if image.viewer.column < viewer.nebula_studio.columns - 1 else im.shape[1]

            cropped = im[y_start : y_end, x_start : x_end]
            print(cropped.shape)

            y_global = displacement[1] * (image.viewer.row + 1)
            x_global = displacement[0] * (image.viewer.column + 1)

            if image.viewer.row == 0:
                y_global -= y
            if image.viewer.column == 0:
                x_global -= x

            big_image[y_global : y_global + (y_end - y_start), x_global : x_global + (x_end - x_start)] = cropped

        # Save the big image
        Image.fromarray(big_image).save(os.path.join(path, f"{self.name}.png"))
