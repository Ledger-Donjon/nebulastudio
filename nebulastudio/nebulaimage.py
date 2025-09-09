from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsSceneMouseEvent,
    QGraphicsPixmapItem,
    QGraphicsSceneContextMenuEvent,
    QMenu,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QPointF
from PIL import Image
import os
import numpy


from .diff import (
    make_rgb_pixmap,
    construct_diff_ndarray,
    normalize_to_8bits,
    apply_balances,
)
from typing import TYPE_CHECKING, cast
import logging

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
            image_to_show = self.image.astype(numpy.int64) - self.average_image.astype(
                numpy.int64
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
                    minmax=self.minmax,
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
        logging.getLogger(__name__).info("Double clicked on image: %s", self.name)
        self.select_in_panel()
        if event is not None:
            event.accept()
        return super().mouseDoubleClickEvent(event)

    def select_in_panel(self):
        """
        Selects the image in the image panel of the Nebula Studio.
        """
        if (ns := self.nebula_studio) is not None:
            ns.image_prop_dock_widget.image_panel.image = self
        else:
            logging.getLogger(__name__).warning(
                "Nebula Studio instance is not available."
            )

    # Context menu settings for the image
    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent | None) -> None:
        """Handles the context menu event for the image."""
        if event is not None:
            if (v := self.viewer) is not None:
                menu = v.context_menu()
            else:
                menu = self.context_menu()
            if menu is not None:
                menu.exec(event.screenPos())
            event.accept()

    def context_menu(self, top_menu: QMenu | None = None) -> QMenu:
        menu = QMenu(top_menu)
        menu.addSection("Selection")
        menu.addAction("Select image", lambda: self.select_in_panel())
        menu.addSection("Alignment")
        ## Get left image
        left_image = self.same_scenario_image(Qt.AlignmentFlag.AlignLeft)
        if left_image is not None:
            menu.addAction(
                f"Align left with {left_image.name}",
                lambda: self.align(Qt.AlignmentFlag.AlignLeft),
            )
        right_image = self.same_scenario_image(Qt.AlignmentFlag.AlignRight)
        if right_image is not None:
            menu.addAction(
                f"Align right with {right_image.name}",
                lambda: self.align(Qt.AlignmentFlag.AlignRight),
            )
        top_image = self.same_scenario_image(Qt.AlignmentFlag.AlignTop)
        if top_image is not None:
            menu.addAction(
                f"Align top with {top_image.name}",
                lambda: self.align(Qt.AlignmentFlag.AlignTop),
            )
        bottom_image = self.same_scenario_image(Qt.AlignmentFlag.AlignBottom)
        if bottom_image is not None:
            menu.addAction(
                f"Align bottom with {bottom_image.name}",
                lambda: self.align(Qt.AlignmentFlag.AlignBottom),
            )

        menu.addAction(
            "Set same offset for all images",
            lambda: self.align(Qt.AlignmentFlag.AlignCenter),
        )
        return menu

    def same_scenario_image(self, direction: Qt.AlignmentFlag):
        """
        Finds the image in the same scenario as this one, in the specified direction.
        """
        if (v := self.viewer) is None or (ns := self.nebula_studio) is None:
            logging.getLogger(__name__).warning("No viewer found for alignment.")
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
            logging.getLogger(__name__).warning(
                "Unknown alignment direction: %s", direction
            )
            return

        # Get image of the same group in the other viewer
        if v2 is None:
            logging.getLogger(__name__).warning(
                "No viewer found in direction %s.", direction
            )
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
            logging.getLogger(__name__).warning("No alignment direction specified.")
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
            logging.getLogger(__name__).warning(
                "No image found in the same scenario in direction %s.", direction.name
            )
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

        ns.alignment_window.set_images(self, image_right, cropping_origin)
        ns.alignment_window.show()
        return ns.alignment_window.alignment_score

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
        logging.getLogger(__name__).info(
            "Setting image settings: %s to %s", value, self.name
        )
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

    def apply_minmax(self, uniform: bool = False):
        """
        Applies the min and max values of the images in the group to all images in the group.
        """
        if uniform:
            minmax = (
                min(
                    image.image.min()
                    for image in self.images
                    if image.image is not None
                ),
                max(
                    image.image.max()
                    for image in self.images
                    if image.image is not None
                ),
            )
        else:
            minmax = None
        logging.getLogger(__name__).info(
            "Applying minmax %s to %d images", minmax, len(self.images)
        )
        for image in self.images:
            if image.image is None:
                continue
            image.minmax = minmax
            image.update_pixmap()
            image.update_tooltip()

    def apply_average(self, do_average: bool):
        """
        Applies the average image to all images in the group.
        If do_average is False, the average image is removed.
        """
        try:
            if not do_average:
                self.average_image = None
                return

            self.average_image = numpy.median(
                numpy.array([image.image for image in self.images]), axis=0
            ).astype(numpy.uint64)

            # Calculate mean pixel value in the shade image (we want to center the
            # data arround zero to make a correction image)
            mean_pixel = numpy.mean(self.average_image, axis=(0, 1))
            self.average_image = self.average_image - mean_pixel

            if self.average_image is None:
                logging.getLogger(__name__).warning("No average image available.")

        finally:
            for image in self.images:
                # image.minmax = (_min, _max)
                image.average_image = self.average_image
                image.update_pixmap()

    def export_images(self, path: str | None = None):
        """
        Stitch all the images of the group into a single image.
        """

        viewer = self.images[0].viewer
        assert viewer is not None
        displacement = viewer.nebula_studio.displacement_size_pixels
        assert displacement is not None
        # Create a big image.
        big_image = numpy.zeros(
            (
                displacement[0] * viewer.nebula_studio.rows + 1000,
                displacement[1] * viewer.nebula_studio.columns + 1000,
                3,
            ),
            dtype=numpy.uint8,
        )

        xmin = big_image.shape[1]
        xmax = 0
        ymin = big_image.shape[0]
        ymax = 0

        for image in self.images:
            if (im := image.image_to_show) is None:
                continue
            if (v := image.viewer) is None:
                continue

            x = int(-image.pos().x() + im.shape[1] / 2 - displacement[0] / 2)
            y = int(-image.pos().y() + im.shape[0] / 2 - displacement[1] / 2)

            y_start = 0 if v.row == 0 else y
            x_start = 0 if v.column == 0 else x

            y_end = (
                (y + displacement[1])
                if v.row < viewer.nebula_studio.rows - 1
                else im.shape[0]
            )
            x_end = (
                (x + displacement[0])
                if v.column < viewer.nebula_studio.columns - 1
                else im.shape[1]
            )

            # Make a copy of the image to avoid modifying the original
            im2 = im.astype(numpy.uint64)
            # Convert the numpy array to a PIL image
            im2 = normalize_to_8bits(
                im2,
                min=image.minmax[0] if image.minmax else None,
                max=image.minmax[1] if image.minmax else None,
            )
            im2 = apply_balances(im2, image.balances)

            cropped = im2[y_start:y_end, x_start:x_end]

            y_global = displacement[1] * (v.row + 1)
            x_global = displacement[0] * (v.column + 1)

            if v.row == 0:
                y_global -= y
            if v.column == 0:
                x_global -= x

            x_global_top = x_global + (x_end - x_start)
            y_global_top = y_global + (y_end - y_start)

            big_image[
                y_global : y_global + (y_end - y_start),
                x_global : x_global + (x_end - x_start),
            ] = cropped

            xmin = min(xmin, x_global)
            xmax = max(xmax, x_global_top)
            ymin = min(ymin, y_global)
            ymax = max(ymax, y_global_top)

        big_image = big_image[ymin:ymax, xmin:xmax]

        # Ask the user where to store the big image
        path, _ = QFileDialog.getSaveFileName(
            None,
            "Save big image",
            f"{self.name}.png",
            "PNG files (*.png)",
        )
        logging.getLogger(__name__).info("Saving big image to %s", path)
        if not path:
            return

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        # Save the big image
        Image.fromarray(big_image).save(path)
