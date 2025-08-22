from typing import TYPE_CHECKING
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QPushButton,
    QHBoxLayout,
    QLabel,
)

if TYPE_CHECKING:
    from ..nebulastudio import NebulaStudio


class ViewersSelectionDockWidget(QDockWidget):
    """
    Dock widget to select ranges of viewers (rows/columns) to show or hide.
    """

    def __init__(self, nebula_studio: "NebulaStudio"):
        super().__init__("Viewers Selection")
        self.nebula_studio = nebula_studio

        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        self._is_updating = False

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        container.setLayout(layout)

        # Row range group
        self.row_group = QGroupBox("Rows range (inclusive)")
        row_form = QFormLayout()
        self.row_min = QSpinBox()
        self.row_max = QSpinBox()
        row_form.addRow("Min row", self.row_min)
        row_form.addRow("Max row", self.row_max)
        self.row_group.setLayout(row_form)

        # Column range group
        self.col_group = QGroupBox("Columns range (inclusive)")
        col_form = QFormLayout()
        self.col_min = QSpinBox()
        self.col_max = QSpinBox()
        col_form.addRow("Min column", self.col_min)
        col_form.addRow("Max column", self.col_max)
        self.col_group.setLayout(col_form)

        # Actions
        actions = QHBoxLayout()
        self.reset_btn = QPushButton("Reset")
        self.apply_label = QLabel("Changes apply immediately")
        self.apply_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        actions.addWidget(self.reset_btn)
        actions.addStretch(1)
        actions.addWidget(self.apply_label)

        layout.addWidget(self.row_group)
        layout.addWidget(self.col_group)
        layout.addLayout(actions)
        layout.addStretch(1)
        self.setWidget(container)

        # Wire signals
        self.row_min.valueChanged.connect(self._on_range_changed)
        self.row_max.valueChanged.connect(self._on_range_changed)
        self.col_min.valueChanged.connect(self._on_range_changed)
        self.col_max.valueChanged.connect(self._on_range_changed)
        self.reset_btn.clicked.connect(self.reset_ranges)

        # Initialize ranges/values
        self.sync_ranges()

    def sync_ranges(self):
        """
        Synchronize spin boxes ranges with the current grid size.
        """
        self._is_updating = True
        try:
            max_row = max(self.nebula_studio.rows - 1, 0)
            max_col = max(self.nebula_studio.columns - 1, 0)

            for sb in (self.row_min, self.row_max):
                sb.setMinimum(0)
                sb.setMaximum(max_row)
            for sb in (self.col_min, self.col_max):
                sb.setMinimum(0)
                sb.setMaximum(max_col)

            # Preserve current selection if possible; otherwise clamp/reset
            self.row_min.setValue(min(self.row_min.value(), max_row))
            self.row_max.setValue(
                max(self.row_min.value(), min(self.row_max.value(), max_row))
            )
            self.col_min.setValue(min(self.col_min.value(), max_col))
            self.col_max.setValue(
                max(self.col_min.value(), min(self.col_max.value(), max_col))
            )

            # If widget was just created (all zeros), default to full range
            if self.row_max.value() == 0 and max_row > 0:
                self.row_max.setValue(max_row)
            if self.col_max.value() == 0 and max_col > 0:
                self.col_max.setValue(max_col)
        finally:
            self._is_updating = False
        # Apply current selection
        self._apply_visibility()

    def reset_ranges(self):
        self._is_updating = True
        try:
            self.row_min.setValue(0)
            self.row_max.setValue(max(self.nebula_studio.rows - 1, 0))
            self.col_min.setValue(0)
            self.col_max.setValue(max(self.nebula_studio.columns - 1, 0))
        finally:
            self._is_updating = False
        self._apply_visibility()

    def _on_range_changed(self, _value: int):
        if self._is_updating:
            return
        # Enforce min <= max for both axes
        self._is_updating = True
        try:
            if self.row_min.value() > self.row_max.value():
                self.row_max.setValue(self.row_min.value())
            if self.col_min.value() > self.col_max.value():
                self.col_max.setValue(self.col_min.value())
        finally:
            self._is_updating = False
        self._apply_visibility()

    def _apply_visibility(self):
        self.nebula_studio.update_viewers_visibility(
            self.row_min.value(),
            self.row_max.value(),
            self.col_min.value(),
            self.col_max.value(),
        )
