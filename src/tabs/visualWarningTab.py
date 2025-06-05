import sys
from PyQt6.QtCore import QTimer, Qt, pyqtSignal # Import pyqtSignal
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QLabel,
    QSpinBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QColorDialog,
    QSizePolicy
)

class VisualWarningTab(QWidget):
    """
    Handles visual warning logic and UI, managing its state from config.
    Acts as the widget for the 'Visual Warning' tab.
    Allows warning display on the main target or a separate window.
    Includes color selection.
    Emits settingsChanged signal when user modifies settings.
    """

    settingsChanged = pyqtSignal()
    separateWindowClosed = pyqtSignal()

    def __init__(self, targetWidget, configData=None, parent=None):
        """
        Initializes the VisualWarningHandler.

        Args:
            targetWidget (QWidget): The primary widget whose background can be flashed.
            configData (dict): Dictionary containing initial settings.
            parent (QWidget, optional): Parent widget. Defaults to None.
        """
        super().__init__(parent)

        if targetWidget is None:
             print("Warning: No targetWidget provided for VisualWarningTab. Using internal dummy.")
             self._internal_target_widget = QWidget()
             self.targetWidget = self._internal_target_widget
             self.targetWidget.setMinimumSize(200, 100)
        else:
            self.targetWidget = targetWidget
            self._internal_target_widget = None 

        self.originalPalette = self.targetWidget.palette()
        self.warningActive = False

        # --- State for Separate Warning Window ---
        self.alternate_warning_window = None
        self.alternate_window_original_palette = None
        self.alternate_window_timer = QTimer(self)
        self.alternate_window_timer.setSingleShot(True)
        self.alternate_window_timer.timeout.connect(self._reset_alternate_window_warning)

        if configData is None:
            configData = {}

        # --- Load Configuration ---
        initialEnabled = configData.get('enableVisualCheck', 'True').lower() == 'true'
        initialUseSeparate = configData.get('useSeparateWindow', 'False').lower() == 'true'
        try:
            initialDurationMs = int(configData.get('flashDurationMs', '300'))
            if initialDurationMs <= 0: initialDurationMs = 300
        except (ValueError, TypeError):
            initialDurationMs = 300

        initialColorStr = configData.get('warningColor', 'red')
        initialColor = QColor(initialColorStr)
        if not initialColor.isValid():
            print(f"Warning: Invalid color '{initialColorStr}' in config. Defaulting to red.")
            initialColor = QColor('red')

        self.enabled = initialEnabled
        self.flashDurationMs = initialDurationMs
        self.warningColor = initialColor

        # --- Timer for Main Target ---
        self.warningtimer = QTimer(self) 
        self.warningtimer.setSingleShot(True)
        self.warningtimer.timeout.connect(self._reset_visual_warning)

        # === UI ELEMENTS ===
        self.visual_layout = QVBoxLayout(self)
        self._init_enable_checkbox()
        self._init_duration_control()
        self._init_color_picker()
        self._init_separate_window_checkbox(initialUseSeparate)
        self.visual_layout.addStretch()

        # --- Ensure initial state is consistent ---
        if self.use_separate_window_check.isChecked():
             print("Initial state: Separate window enabled. Ensuring window exists.")
             QTimer.singleShot(0, self._ensure_alternate_window_exists_on_init)


    def _ensure_alternate_window_exists_on_init(self):
        """Helper called shortly after init if separate window is initially checked."""
        if self.use_separate_window_check.isChecked(): 
            if not self._ensure_alternate_window_exists():
                print("Error: Failed to create/show alternate window during initialization.")
                self.use_separate_window_check.blockSignals(True)
                self.use_separate_window_check.setChecked(False)
                self.use_separate_window_check.blockSignals(False)


    def _init_enable_checkbox(self):
        self.enable_check = QCheckBox("Enable Visual Warning", self)
        self.enable_check.setChecked(self.enabled)
        self.enable_check.stateChanged.connect(self._handle_enable_change)
        self.visual_layout.addWidget(self.enable_check)

    def _init_duration_control(self):
        duration_layout = QHBoxLayout()
        self.flash_duration_label = QLabel("Flash Duration (ms):", self)
        self.flash_duration_input = QSpinBox(self)
        self.flash_duration_input.setRange(50, 5000)
        self.flash_duration_input.setSingleStep(50)
        self.flash_duration_input.setMaximumWidth(100)
        self.flash_duration_input.setValue(self.flashDurationMs)
        self.flash_duration_input.valueChanged.connect(self._handle_duration_change)

        duration_layout.addWidget(self.flash_duration_label)
        duration_layout.addWidget(self.flash_duration_input)
        duration_layout.addStretch()
        self.visual_layout.addLayout(duration_layout)

    def _init_color_picker(self):
        color_layout = QHBoxLayout()
        self.color_button = QPushButton("Select Warning Color", self)
        self.color_button.clicked.connect(self._select_warning_color)

        self.color_preview_label = QLabel("Current Color:", self)
        self.color_preview = QLabel(self)
        self.color_preview.setFixedSize(30, 20)
        self.color_preview.setAutoFillBackground(True)
        self.color_preview.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_color_preview()

        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_preview_label)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        self.visual_layout.addLayout(color_layout)

    def _init_separate_window_checkbox(self, initial_state):
        """Initializes the checkbox to control warning destination."""
        self.use_separate_window_check = QCheckBox("Show Warning in Separate Window", self)
        self.use_separate_window_check.setChecked(initial_state)
        self.use_separate_window_check.stateChanged.connect(self._handle_separate_window_change)
        self.visual_layout.addWidget(self.use_separate_window_check)

    # --- Event Handlers / Slots ---

    def _select_warning_color(self):
        new_color = QColorDialog.getColor(self.warningColor, self, "Select Warning Color")
        if new_color.isValid():
            if self.warningColor != new_color:
                self.warningColor = new_color
                self._update_color_preview()
                print("Color changed, emitting settingsChanged.")
                self.settingsChanged.emit()

    def _update_color_preview(self):
        palette = self.color_preview.palette()
        palette.setColor(QPalette.ColorRole.Window, self.warningColor)
        self.color_preview.setPalette(palette)

    def _handle_enable_change(self, state):
        if self.enabled != bool(state):
            self.setEnabled(bool(state))
            print("Enable checkbox changed, emitting settingsChanged.")
            self.settingsChanged.emit()

    def _handle_duration_change(self, value):
        if self.flashDurationMs != value:
            self.setFlashDuration(value)
            print("Duration changed, emitting settingsChanged.")
            self.settingsChanged.emit()

    def _handle_separate_window_change(self, state):
        """Handles changes to the 'Use Separate Window' checkbox."""
        use_separate = bool(state)

        if use_separate:
            print("Separate window checkbox checked. Ensuring window exists.")
            if not self._ensure_alternate_window_exists():
                print("Error: Failed to create/show alternate window immediately.")
                self.use_separate_window_check.blockSignals(True)
                self.use_separate_window_check.setChecked(False)
                self.use_separate_window_check.blockSignals(False)
                return 
        else:
            print("Separate window checkbox unchecked. Destroying window.")
            self._destroy_alternate_window()

        print("Separate window checkbox changed, emitting settingsChanged.")
        self.settingsChanged.emit()


    def _handle_alternate_window_closed(self):
        """Slot connected to the destroyed signal of the alternate window."""
        print("Separate warning window closed by user.")
        was_checked = self.use_separate_window_check.isChecked()

        self.alternate_warning_window = None
        self.alternate_window_original_palette = None
        self.alternate_window_timer.stop()

        if self.use_separate_window_check.isChecked():
            self.use_separate_window_check.blockSignals(True)
            self.use_separate_window_check.setChecked(False)
            self.use_separate_window_check.blockSignals(False)

        self.separateWindowClosed.emit()

        if was_checked:
             print("Alternate window closed by user, emitting settingsChanged.")
             self.settingsChanged.emit()


    # --- Public Methods ---

    def setEnabled(self, enabled):
        """Enables or disables the visual warning feature entirely."""
        if isinstance(enabled, int): enabled = bool(enabled)
        self.enabled = enabled 
        if self.enable_check.isChecked() != self.enabled:
            self.enable_check.setChecked(self.enabled)

        if not enabled:
            if self.warningActive:
                self._reset_visual_warning()
                self.warningtimer.stop()
            if self.alternate_window_timer.isActive():
                self._reset_alternate_window_warning()
                self.alternate_window_timer.stop()
            if self.use_separate_window_check.isChecked():
                 print("Visual warning disabled, destroying separate window.")
                 self._destroy_alternate_window()


    def isEnabled(self):
         return self.enabled

    def setFlashDuration(self, duration_ms):
        try:
            duration = int(duration_ms)
            if duration > 0:
                self.flashDurationMs = duration # Update internal state
                if self.flash_duration_input.value() != self.flashDurationMs:
                    self.flash_duration_input.blockSignals(True)
                    self.flash_duration_input.setValue(self.flashDurationMs)
                    self.flash_duration_input.blockSignals(False)
            else:
                print(f"Warning: Duration must be positive.")
                if self.flash_duration_input.value() != self.flashDurationMs:
                     self.flash_duration_input.blockSignals(True)
                     self.flash_duration_input.setValue(self.flashDurationMs)
                     self.flash_duration_input.blockSignals(False)
        except (ValueError, TypeError):
            print(f"Warning: Invalid duration value.")
            if self.flash_duration_input.value() != self.flashDurationMs:
                 self.flash_duration_input.blockSignals(True)
                 self.flash_duration_input.setValue(self.flashDurationMs)
                 self.flash_duration_input.blockSignals(False)


    def get_config_values(self):
        """Returns the current UI state as a dictionary for saving."""
        return {
            "enableVisualCheck": str(self.enable_check.isChecked()),
            "flashDurationMs": str(self.flash_duration_input.value()),
            "warningColor": self.warningColor.name(),
            "useSeparateWindow": str(self.use_separate_window_check.isChecked())
        }

    def trigger(self):
        """Triggers the visual warning based on current settings."""
        if not self.enabled:
            return

        if self.use_separate_window_check.isChecked():
            self._trigger_alternate_warning()
        else:
            self._trigger_main_warning()

    def _trigger_main_warning(self):
        """Triggers the flash on the main target widget."""
        if self.warningActive or self.warningtimer.isActive():
            return
        self.warningActive = True
        try:
            if self.targetWidget and self.targetWidget.isWindow():
                self.originalPalette = self.targetWidget.palette()
            else:
                 print("Main target invalid before flashing.")
                 self.warningActive = False
                 return
        except RuntimeError:
             print("Error getting main target palette before flash (deleted?).")
             self.warningActive = False
             return

        self._flash_widget(self.targetWidget, self.originalPalette, self.warningtimer)

    def _trigger_alternate_warning(self):
        """Ensures the separate window exists and triggers the flash on it."""
        if self.alternate_window_timer.isActive():
             return 

        if not self.alternate_warning_window or not self.alternate_warning_window.isWindow():
             print("Alternate window missing or invalid when triggering. Attempting recovery.")
             if not self._ensure_alternate_window_exists():
                 print("Error: Could not recover alternate warning window.")
                 self.use_separate_window_check.blockSignals(True)
                 self.use_separate_window_check.setChecked(False)
                 self.use_separate_window_check.blockSignals(False)
                 return 

        try:
            if self.alternate_warning_window and self.alternate_warning_window.isWindow():
                 self.alternate_window_original_palette = self.alternate_warning_window.palette()
            else:
                 print("Alternate window invalid before getting palette for flash.")
                 return 
        except RuntimeError:
             print("Error getting alternate window palette before flash (deleted?).")
             return

        self._flash_widget(self.alternate_warning_window, self.alternate_window_original_palette, self.alternate_window_timer)


    def _ensure_alternate_window_exists(self):
        """Creates the alternate window if needed, ensures it's visible. Returns True on success."""
        window_valid = False
        if self.alternate_warning_window:
            try:
                if self.alternate_warning_window.isWindow():
                    window_valid = True
            except RuntimeError:
                print("Alternate warning window was deleted externally.")
                self.alternate_warning_window = None
                window_valid = False

        if not window_valid:
            print("Creating new alternate warning window.")
            self.alternate_warning_window = QWidget()
            self.alternate_warning_window.setWindowFlags(Qt.WindowType.Window)
            self.alternate_warning_window.setWindowTitle("Visual Warning Display")
            self.alternate_warning_window.setGeometry(200, 200, 300, 150)
            self.alternate_window_original_palette = self.alternate_warning_window.palette()
            try: 
                self.alternate_warning_window.destroyed.disconnect(self._handle_alternate_window_closed)
            except TypeError: pass 
            self.alternate_warning_window.destroyed.connect(self._handle_alternate_window_closed)
            window_valid = True 

        if window_valid and self.alternate_warning_window:
             try:
                self.alternate_warning_window.show()
                self.alternate_warning_window.raise_()
                self.alternate_warning_window.activateWindow()
                return True
             except RuntimeError:
                 print("Error showing/raising alternate window (already deleted?).")
                 self.alternate_warning_window = None
                 return False
        return False


    def _flash_widget(self, widget, original_palette_ref, timer):
        """
        Applies the warning color flash to the specified widget.
        Uses the provided original_palette_ref for reset.
        """
        try:
            if not widget or not widget.isWindow():
                 print(f"Warning: Target widget {widget} for flash is invalid or deleted.")
                 if timer.isActive(): timer.stop()
                 if widget == self.targetWidget: self.warningActive = False
                 return

            flash_palette = QPalette(original_palette_ref)
            flash_palette.setColor(QPalette.ColorRole.Window, self.warningColor)
            widget.setPalette(flash_palette)
            widget.setAutoFillBackground(True) 
            widget.update() 

            timer.start(self.flashDurationMs)

        except RuntimeError as e:
            print(f"Error flashing widget {widget} (it might have been deleted): {e}")
            if timer.isActive(): timer.stop()
            if widget == self.targetWidget: self.warningActive = False


    def _reset_visual_warning(self):
        """Resets the main target widget background."""
        try:
            if self.targetWidget and self.targetWidget.isWindow():
                self.targetWidget.setPalette(self.originalPalette)
                self.targetWidget.update()
        except RuntimeError:
            print("Error resetting main target widget (already deleted?).")
        finally:
            self.warningActive = False


    def _reset_alternate_window_warning(self):
        """Resets the alternate warning window background."""
        try:
            if self.alternate_warning_window and self.alternate_warning_window.isWindow():
                 if self.alternate_window_original_palette:
                    self.alternate_warning_window.setPalette(self.alternate_window_original_palette)
                    self.alternate_warning_window.update()
                 else:
                      print("Warning: Original palette for alternate window missing on reset.")
        except RuntimeError:
            print("Error resetting alternate window (already deleted?).")


    def _destroy_alternate_window(self):
        """Safely closes and cleans up the alternate warning window."""
        if self.alternate_warning_window:
            print("Closing alternate warning window.")
            self.alternate_window_timer.stop()
            try:
                self.alternate_warning_window.destroyed.disconnect(self._handle_alternate_window_closed)
            except (TypeError, RuntimeError): pass
            try:
                if self.alternate_warning_window.isWindow():
                    self.alternate_warning_window.close()
            except RuntimeError:
                 print("Alternate window already deleted when trying to close.")
            self.alternate_warning_window = None
            self.alternate_window_original_palette = None


    def closeEvent(self, event):
        """Ensure alternate window is closed when the tab itself is closed."""
        print("Closing VisualWarningTab, ensuring alternate window is destroyed.")
        self._destroy_alternate_window()
        super().closeEvent(event)