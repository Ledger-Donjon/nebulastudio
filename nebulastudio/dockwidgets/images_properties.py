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
    QDockWidget,
    QVBoxLayout,
    QWidget,
)
from ..nebulaimage import NebulaImage, NebulaImageGroup, make_rgb_pixmap
from ..viewer import Viewer

if TYPE_CHECKING:
    from ..nebulastudio import NebulaStudio


class ImagePropertiesPanel(QGroupBox):
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

        self.opacity_button = w = QPushButton("Opacity")
        form.addRow(w, hbox)
        w.setCheckable(True)
        w.setChecked(True)
        w.clicked.connect(self._on_opacity_button_clicked)
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

        self.average_button = QPushButton("Remove Shading")
        self.average_button.setCheckable(True)
        self.average_button.setToolTip(
            "Remove the median value of all pixels for all images of this group."
        )
        self.average_button.toggled.connect(self.on_shading_button_clicked)
        self.form.addRow("Shading", self.average_button)

        self.uniform_button = QPushButton("Uniform")
        self.uniform_button.setCheckable(True)
        self.uniform_button.setToolTip(
            "Apply the min and max values of all images to all images of this group for uniform."
        )
        self.uniform_button.toggled.connect(self.on_uniform_button_clicked)
        self.form.addRow("Uniform", self.uniform_button)

        self.export_button = QPushButton("Export")
        self.export_button.setToolTip("Export the image to a file")
        self.export_button.clicked.connect(self.on_export_button_clicked)
        self.form.addRow("Export", self.export_button)

        self._image: NebulaImage | None = None

    def on_export_button_clicked(self):
        """
        Handles the export button click event.
        """
        if not isinstance(image := self.image, NebulaImageGroup):
            return
        image.export_images(os.path.join(os.path.expanduser("~"), "Desktop", "export"))

    def on_uniform_button_clicked(self, checked: bool):
        """
        Handles the uniform button click event.
        """
        if not isinstance(image := self.image, NebulaImageGroup):
            return
        image.apply_minmax(checked)

    def on_shading_button_clicked(self, checked: bool):
        """
        Handles the shading button click event.
        This method should implement the logic to remove the median value of all pixels for all images of this group.
        """
        # This only works for groups of images
        if not isinstance(image := self.image, NebulaImageGroup):
            return

        image.apply_average(checked)

        # Show the result in a new window
        if image.average_image is not None:
            average_image = make_rgb_pixmap(image.average_image)
            self.average_window = QLabel()
            self.average_window.setPixmap(average_image)
            self.average_window.show()
            self.average_window.setWindowTitle(f"Average of {image.name}")

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

        name = self._image.name
        if isinstance(self._image, NebulaImageGroup):
            name = f"{name} (Group of {len(self._image.images)} images)"
        self.setTitle(name)

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

    def _on_opacity_button_clicked(self, checked: bool):
        """
        Handles the opacity button click event.
        """
        self._on_opacity_changed(100 if checked else 0)

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
        self.opacity_button.blockSignals(True)

        self.opacity_button.setChecked(opacity > 0)
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
        self.opacity_button.blockSignals(False)

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


class ImagesPropertiesDockWidget(QDockWidget):
    """
    A panel for adjusting the properties of Nebula Studio.
    """

    def __init__(self, nebula_studio: "NebulaStudio"):
        """
        Initializes the DockWidget instance.
        """
        super().__init__()
        self.nebula_studio = nebula_studio
        self.image_panel = ImagePropertiesPanel()

        # Dropdown list to select the image
        self.image_selector = QPushButton("Selection")
        self.setWindowFlag(Qt.WindowType.WindowTitleHint, True)
        self.setWidget(w := QWidget())
        w.setLayout(vbox := QVBoxLayout())
        vbox.addWidget(self.image_selector)
        vbox.addWidget(self.image_panel)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        self.dockLocationChanged.connect(self.dock_widget_area_changed)

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
                viewer_menu.addSeparator()
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
            scenario_menu.addSeparator()
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
        self.dock_widget_area_changed()

    def dock_widget_area_changed(self):
        """
        Handles the dock widget area change event.
        """
        if image := self.image_panel.image:
            name = image.name
            # Check if docked
            if self.isFloating():
                name += " - " + self.nebula_studio.windowTitle()
        else:
            name = self.nebula_studio.windowTitle()
        self.setWindowTitle(name)
