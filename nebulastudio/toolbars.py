import os
from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QSlider,
    QLabel,
    QFormLayout,
    QDoubleSpinBox,
    QPushButton,
    QMenu,
    QDockWidget,
    QGridLayout,
    QVBoxLayout,
    QWidget,
)
from .nebulaimage import NebulaImage, NebulaImageGroup
from .viewer import Viewer

if TYPE_CHECKING:
    from .nebulastudio import NebulaStudio


class NebulaImagePanel(QGroupBox):
    """
    A panel for adjusting an image in Nebula Studio.
    """

    def __init__(self):
        """
        Initializes the NebulaImagePanel instance.

        Args:
            image (NebulaImage): The image to display.
        """
        super().__init__()
        self.setLayout(form := QFormLayout())
        self.opacity_slider = slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_spinner = spinbox = QDoubleSpinBox()
        slider.setToolTip("Adjust the opacity of the image")
        slider.setValue(100)
        slider.setRange(0, 100)
        spinbox.setRange(0, 100)
        spinbox.setSingleStep(1)
        spinbox.setValue(100)
        spinbox.setSuffix("%")
        spinbox.setToolTip("Adjust the opacity of the image")
        hbox = QHBoxLayout()
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)
        form.addRow("Opacity", hbox)
        slider.valueChanged.connect(self._on_opacity_changed)
        spinbox.valueChanged.connect(self._on_opacity_changed)

        self.white_level_slider = slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setSingleStep(1)
        slider.setValue(100)
        slider.setToolTip("Adjust the white balance of the image")
        self.white_level_spinner = spinbox = QDoubleSpinBox()
        spinbox.setRange(0, 100)
        spinbox.setSingleStep(1)
        spinbox.setValue(100)
        spinbox.setSuffix("%")
        spinbox.setToolTip("Adjust the white balance of the image")
        hbox = QHBoxLayout()
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)
        form.addRow("White Balance", hbox)
        slider.valueChanged.connect(self._on_white_level_changed)
        spinbox.valueChanged.connect(self._on_white_level_changed)

        self.black_level_slider = slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setSingleStep(1)
        slider.setValue(0)
        slider.setToolTip("Adjust the black level of the image")
        self.black_level_spinner = spinbox = QDoubleSpinBox()
        spinbox.setRange(0, 100)
        spinbox.setSingleStep(1)
        spinbox.setValue(0)
        spinbox.setSuffix("%")
        spinbox.setToolTip("Adjust the black level of the image")
        hbox = QHBoxLayout()
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)
        form.addRow("Black Level", hbox)
        slider.valueChanged.connect(self._on_black_level_changed)
        spinbox.valueChanged.connect(self._on_black_level_changed)

        # Constant Offset

        self.offset_x_slider = slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-100, 100)
        slider.setSingleStep(1)
        slider.setValue(0)
        slider.setToolTip("Adjust the X offset of the image")
        self.offset_x_spinner = spinbox = QDoubleSpinBox()
        spinbox.setRange(-100, 100)
        spinbox.setSingleStep(1)
        spinbox.setValue(0)
        spinbox.setSuffix("px")
        spinbox.setToolTip("Adjust the X offset of the image")
        hbox = QHBoxLayout()
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)
        form.addRow("X Offset", hbox)
        slider.valueChanged.connect(self._on_pos_x_changed)
        slider.sliderReleased.connect(self.recenter_pos_sliders)
        spinbox.valueChanged.connect(self._on_pos_x_changed)

        self.offset_y_slider = slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-100, 100)
        slider.setSingleStep(1)
        slider.setValue(0)
        slider.setToolTip("Adjust the Y offset of the image")
        self.offset_y_spinner = spinbox = QDoubleSpinBox()
        spinbox.setRange(-100, 100)
        spinbox.setSingleStep(1)
        spinbox.setValue(0)
        spinbox.setSuffix("px")
        spinbox.setToolTip("Adjust the Y offset of the image")
        hbox = QHBoxLayout()
        hbox.addWidget(slider)
        hbox.addWidget(spinbox)
        form.addRow("Y Offset", hbox)
        slider.valueChanged.connect(self._on_pos_y_changed)
        slider.sliderReleased.connect(self.recenter_pos_sliders)
        spinbox.valueChanged.connect(self._on_pos_y_changed)

        self.image_url = w = QLabel()
        form.addRow("Name", w)
        self.reference_url = w = QLabel()
        form.addRow("Reference", w)
        self.form = form
        self.setEnabled(False)

        self.average_button = QPushButton("Average Images")
        self.average_button.setToolTip("Average all the images to normalize.")
        self.average_button.clicked.connect(self.on_average_button_clicked)
        self.form.addRow("Average", self.average_button)

    def on_average_button_clicked(self):
        """
        Handles the average button click event.
        This method should implement the logic to average all images in the Nebula Studio.
        """
        # Get all images of the group
        if not isinstance(image := self.image, NebulaImageGroup):
            return
        image.apply_average()

        self.average = QLabel()
        from .nebulaimage import make_rgb_pixmap

        assert image.average_image is not None, "Average image should not be None"
        self.average.setPixmap(make_rgb_pixmap(image.average_image))
        self.average.show()

    @property
    def image(self) -> NebulaImage | None:
        """
        Returns the image associated with this panel.
        """
        return self._image

    @image.setter
    def image(self, value: NebulaImage | None):
        """
        Sets the image associated with this panel.
        """
        if value is None:
            self._image = None
            self.hide()
            return
        self._image = value

        self.setTitle(self._image.name)
        if self._image.diff_image is not None:
            self.setWindowTitle(self._image.name)

        self.image_url.setText(self._image.name)
        self.image_url.setToolTip(self._image.pattern)
        row = self.form.getWidgetPosition(self.reference_url)

        if self._image.reference_url is None:
            if row is not None and row[0] is not None:
                self.form.setRowVisible(row[0], False)
        else:
            self.reference_url.setText(os.path.basename(self._image.reference_url))
            self.reference_url.setToolTip(self._image.reference_pattern)
            if row is not None and row[0] is not None:
                self.form.setRowVisible(row[0], True)

        self.update_ui()

    @property
    def images(self) -> list[NebulaImage]:
        """
        Returns a list of images associated with this panel.
        """
        if (img := self.image) is None:
            return []
        return [img] + (list(img.images) if isinstance(img, NebulaImageGroup) else [])

    def _on_opacity_changed(self, value: int | float):
        """
        Handles the opacity change event.

        Args:
            value (int | float): The new opacity value.
        """
        for image in self.images:
            image.setOpacity(value / 100.0)
            image.update()
            if scene := image.scene():
                scene.update()
        self.update_ui()

    def _on_white_level_changed(self, value: int | float):
        """
        Handles the white balance change event.

        Args:
            value (int | float): The new white balance value.
        """
        for image in self.images:
            image.balances = (image.balances[0], value / 100.0)
            image.update_pixmap()
            if scene := image.scene():
                scene.update()
        self.update_ui()

    def _on_black_level_changed(self, value: int | float):
        """
        Handles the black level change event.

        Args:
            value (int): The new black level value.
        """
        for image in self.images:
            image.balances = (value / 100.0, image.balances[1])
            image.update_pixmap()
            if scene := image.scene():
                scene.update()
        self.update_ui()

    def _on_pos_x_changed(self, value: int | float):
        """
        Handles the X offset change event.

        Args:
            value (int | float): The new X offset value.
        """
        for image in self.images:
            image.setPos(float(value), image.pos().y())
            image.update()
            if scene := image.scene():
                scene.update()
        self.update_ui()

        # TODO REMOVE
        self.images[0].align()

    def _on_pos_y_changed(self, value: int | float):
        """
        Handles the Y offset change event.

        Args:
            value (int): The new Y offset value.
        """
        for image in self.images:
            image.setPos(image.pos().x(), float(value))
            image.update()
            if scene := image.scene():
                scene.update()
        self.update_ui()

        # TODO REMOVE
        self.images[0].align()

    def update_ui(self):
        """
        Updates the UI of the panel.
        """
        if self.image is None:
            self.setEnabled(False)
            self.setTitle("No Image")
            return
        self.setEnabled(True)
        opacity = self.image.opacity()
        white_level = self.image.balances[1]
        black_level = self.image.balances[0]

        self.black_level_slider.blockSignals(True)
        self.black_level_spinner.blockSignals(True)
        self.white_level_slider.blockSignals(True)
        self.white_level_spinner.blockSignals(True)
        self.opacity_slider.blockSignals(True)
        self.opacity_spinner.blockSignals(True)
        self.offset_x_spinner.blockSignals(True)
        self.offset_y_spinner.blockSignals(True)

        self.black_level_spinner.setValue(black_level * 100)
        self.black_level_slider.setValue(int(black_level * 100))
        self.white_level_spinner.setValue(white_level * 100)
        self.white_level_slider.setValue(int(white_level * 100))
        self.opacity_spinner.setValue(opacity * 100)
        self.opacity_slider.setValue(int(opacity * 100))
        self.offset_x_spinner.setValue(self.image.pos().x())
        self.offset_y_spinner.setValue(self.image.pos().y())
        self.recenter_pos_sliders()

        self.opacity_slider.blockSignals(False)
        self.opacity_spinner.blockSignals(False)
        self.white_level_slider.blockSignals(False)
        self.white_level_spinner.blockSignals(False)
        self.black_level_slider.blockSignals(False)
        self.black_level_spinner.blockSignals(False)
        self.offset_x_spinner.blockSignals(False)
        self.offset_y_spinner.blockSignals(False)

        self.average_button.setEnabled(isinstance(self.image, NebulaImageGroup))

    def recenter_pos_sliders(self):
        """
        Re-centers the position sliders.
        """
        if self.image is None:
            return
        pos_x = int(self.image.pos().x())
        pos_y = int(self.image.pos().y())

        self.offset_x_slider.blockSignals(True)
        self.offset_y_slider.blockSignals(True)

        self.offset_x_slider.setRange(pos_x - 100, pos_x + 100)
        # self.offset_x_slider.setValue(pos_x)
        self.offset_y_slider.setRange(pos_y - 100, pos_y + 100)
        # self.offset_y_slider.setValue(pos_y)
        self.offset_x_slider.blockSignals(False)
        self.offset_y_slider.blockSignals(False)


class NebulaStudioToolbox(QDockWidget):
    """
    A panel for adjusting the properties of Nebula Studio.
    """

    def __init__(self, nebula_studio: "NebulaStudio"):
        """
        Initializes the NebulaStudiotoolbox instance.
        """
        super().__init__()
        self.nebula_studio = nebula_studio
        self.image_panel = NebulaImagePanel()
        self.setWindowTitle(nebula_studio.windowTitle() + " - Image Parameters")
        # Dropdown list to select the image
        self.image_selector = QPushButton("Selection")
        self.setWindowFlag(Qt.WindowType.WindowTitleHint, True)
        self.setWidget(w := QWidget())
        w.setLayout(vbox := QVBoxLayout())
        vbox.addWidget(self.image_selector)
        vbox.addWidget(self.image_panel)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

    def update_image_selector(self):
        """
        Updates the image selector with the list of images in the Nebula Studio.
        """
        menu = QMenu(self.image_selector)
        row_menu = viewers = QMenu(menu)
        viewers.setTitle("By position")
        menu.addMenu(viewers)
        patterns = QMenu(menu)
        patterns.setTitle("By scenario")
        menu.addMenu(patterns)
        self.image_selector.setMenu(menu)

        separate_rows = self.nebula_studio.rows > 5
        for i in range(self.nebula_studio.rows):
            if separate_rows:
                row_menu = QMenu(viewers)
                row_menu.setTitle(f"Row {i}")
                viewers.addMenu(row_menu)

            for j in range(self.nebula_studio.columns):
                viewer = self.nebula_studio.viewer_at(i, j)
                if not isinstance(viewer, Viewer):
                    continue
                group = viewer.group
                viewer_menu = QMenu(row_menu)
                row_menu.addMenu(viewer_menu)
                viewer_menu.setTitle(
                    f"Column {j}" if separate_rows else group.groupname
                )
                viewer_menu.addAction(
                    "All images",
                    lambda img=group: self.on_image_selected(img),
                )
                for image in group.images:
                    viewer_menu.addAction(
                        image.name,
                        lambda img=image: self.on_image_selected(img),
                    )

        for scenario in self.nebula_studio.scenarios.values():
            scenario_menu = QMenu(patterns)
            scenario_menu.setTitle(scenario.name)
            scenario_menu.addAction(
                "All images",
                lambda img=scenario: self.on_image_selected(img),
            )
            for image in scenario.images:
                scenario_menu.addAction(
                    image.name,
                    lambda img=image: self.on_image_selected(img),
                )
                patterns.addMenu(scenario_menu)

    def on_image_selected(self, image: NebulaImage):
        """
        Handles the image selection event.
        """
        self.image_panel.image = image


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
        self.l, self.r = QLabel(), QLabel()
        self.d, self.s = QLabel(), QLabel()

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

        self._image: NebulaImage | None = None
        self.hide()

        self.topLevelChanged.connect(self.dockWidget_topLevelChanged)

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

    @property
    def image(self) -> NebulaImage | None:
        """
        Returns the image associated with this toolbox.
        """
        return self._image

    @image.setter
    def image(self, value: NebulaImage | None):
        """
        Sets the image associated with this toolbox.
        """
        self._image = value
        if value is None:
            self.hide()
            return
        self.show()

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        # Detect left right, up down arrow keys
        if a0 is not None and (image := self.image) is not None:
            # Detect if shift is pressed
            if a0.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                diff = 10
            else:
                diff = 1

            # Detect the 'n' key
            if a0.key() == Qt.Key.Key_N:
                next_image = image.same_scenario_image(Qt.AlignmentFlag.AlignRight)
                if next_image is not None:
                    self.image = None
                    next_image.last_alignment_direction = Qt.AlignmentFlag.AlignLeft
                    self.image = next_image
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
                    return super().keyPressEvent(a0)

                return super().keyPressEvent(a0)

            # Detect the 'm' key for auto-alignment
            if a0.key() == Qt.Key.Key_M:
                best_pos = init_pos = image.pos()
                res = image.align()
                if res is None:
                    print("Alignment failed")
                    return super().keyPressEvent(a0)

                for x in range(-10 * diff, 11 * diff):
                    for y in range(-10 * diff, 11 * diff):
                        image.setPos(init_pos.x() + x, init_pos.y() + y)
                        score = image.align()
                        if score is not None and score < res:
                            res = score
                            best_pos = image.pos()
                image.setPos(best_pos)
                image.align()
                return super().keyPressEvent(a0)

            if a0.key() == Qt.Key.Key_Left:
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
        return super().closeEvent(event)
