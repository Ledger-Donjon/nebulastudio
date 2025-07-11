import os
from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QSlider,
    QLabel,
    QFormLayout,
    QDoubleSpinBox,
    QPushButton,
    QMenu,
    QToolBar,
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


class NebulaStudioToolbar(QToolBar):
    """
    A panel for adjusting the properties of Nebula Studio.
    """

    def __init__(self, nebula_studio: "NebulaStudio"):
        """
        Initializes the NebulaStudioToolbar instance.
        """
        super().__init__()
        self.nebula_studio = nebula_studio
        # self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        # self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_panel = NebulaImagePanel()
        self.setWindowTitle(nebula_studio.windowTitle() + " - Image Parameters")
        self.setOrientation(Qt.Orientation.Vertical)
        # Dropdown list to select the image
        self.title = QLabel(self.windowTitle())
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_action = self.addWidget(self.title)
        self.removeAction(self.title_action)
        self.image_selector = QPushButton("Selection")
        self.image_selector_action = self.addWidget(self.image_selector)
        self.addWidget(self.image_panel)

        self.orientationChanged.connect(self.orientation_changed)
        self.topLevelChanged.connect(self.floating_changed)
        self.setWindowFlag(Qt.WindowType.WindowTitleHint, True)

    def floating_changed(self, floating: bool):
        if floating:
            self.insertAction(self.image_selector_action, self.title_action)
            self.title.setText(self.nebula_studio.windowTitle())
        else:
            self.removeAction(self.title_action)

    def orientation_changed(self, orientation: Qt.Orientation):
        """Force to be always vertical"""
        if orientation == Qt.Orientation.Horizontal:
            self.setOrientation(Qt.Orientation.Vertical)

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

    # def closeEvent(self, a0: QCloseEvent | None) -> None:

    #     return
