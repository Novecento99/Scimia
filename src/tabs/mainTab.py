
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QProgressBar, QSlider, QLineEdit, QLabel, QDial, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal
import traceback

class MainTab(QWidget):
    """
    Manages the UI elements and logic for the 'Main' tab,
    including volume monitoring, gain, threshold, and trigger controls.

    Accepts initial configuration data during construction.
    """
    gain_changed = pyqtSignal(int)
    threshold_changed = pyqtSignal(int)
    trigger_enabled_changed = pyqtSignal(bool)
    mute_enabled_changed = pyqtSignal(bool)
    settings_changed = pyqtSignal() 

    def __init__(self, configData=None, parent=None):
        """
        Initializes the MainTab and applies initial settings from configData.

        Args:
            configData (dict, optional): Dictionary containing initial settings
                                         for 'gainBox', 'thresholdBox', 'triggerCheck',
                                         and 'muteAudioCheck'. Defaults to None.
            parent (QWidget, optional): The parent widget. Defaults to None.
        """
        super().__init__(parent)
        self._is_programmatic_change = False

        # --- UI Elements ---
        configBoxSize = 50
        self.volumeBar = QProgressBar()
        self.volumeBar.setRange(0, 100)
        self.volumeBar.setValue(0)      
        self.volumeBar.setTextVisible(False)
        self.volumeBar.setStyleSheet(
            """
            QProgressBar { border: 1px solid grey; border-radius: 1px; text-align: center; }
            QProgressBar::chunk { background-color: green; }
            """
        )

        self.thresholdSlider = QSlider(Qt.Orientation.Horizontal)
        self.thresholdSlider.setRange(0, 100)
        self.thresholdSlider.setStyleSheet(
            """
            QSlider::groove:horizontal { border: 1px solid #bbb; background: #ddd; height: 8px; border-radius: 4px; }
            QSlider::sub-page:horizontal { background: #66c2ff; border: 1px solid #44a4ee; height: 8px; border-radius: 4px; }
            QSlider::add-page:horizontal { background: #ddd; border: 1px solid #bbb; height: 8px; border-radius: 4px; }
            QSlider::handle:horizontal { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eee, stop:1 #ccc); border: 1px solid #777; width: 16px; margin: -4px 0; border-radius: 8px; }
            """
        )
        self.thresholdBox = QLineEdit()
        self.thresholdBox.setMaximumWidth(configBoxSize)
        self.thresholdLabel = QLabel("- Trigger Threshold")

        self.volumeKnob = QDial()
        self.volumeKnob.setRange(0, 100)
        self.gainBox = QLineEdit()
        self.gainBox.setMaximumWidth(configBoxSize)
        self.gainLabel = QLabel("- Mic Sensitivity (Gain)")

        self.triggerCheck = QCheckBox("Enable Trigger")
        self.muteAudioCheck = QCheckBox("Mute Audio Warning")

        # --- Layouts ---
        mainLayout = QGridLayout(self) 
        gainLayout = QHBoxLayout()
        thresholdLayout = QHBoxLayout()
        triggerControlLayout = QVBoxLayout()

        gainLayout.addWidget(self.gainBox, 0, Qt.AlignmentFlag.AlignLeft)
        gainLayout.addWidget(self.gainLabel, 1, Qt.AlignmentFlag.AlignLeft)
        thresholdLayout.addWidget(self.thresholdBox, 0, Qt.AlignmentFlag.AlignLeft)
        thresholdLayout.addWidget(self.thresholdLabel, 1, Qt.AlignmentFlag.AlignLeft)
        triggerControlLayout.addWidget(self.triggerCheck)
        triggerControlLayout.addWidget(self.muteAudioCheck)
        triggerControlLayout.addStretch()

        mainLayout.addWidget(self.volumeBar, 0, 0, 1, 3)
        mainLayout.addWidget(self.thresholdSlider, 1, 0, 1, 3)
        mainLayout.addWidget(self.volumeKnob, 2, 0, 2, 1)
        mainLayout.addLayout(thresholdLayout, 2, 1)
        mainLayout.addLayout(gainLayout, 3, 1)
        mainLayout.addLayout(triggerControlLayout, 2, 2, 2, 1)

        # --- Apply Initial Settings ---
        initial_config = configData if configData is not None else {}
        self.set_values_from_dict(initial_config)

        # --- Connections ---
        self.volumeKnob.valueChanged.connect(self._set_gain_box_from_knob)
        self.gainBox.textEdited.connect(self._set_volume_knob_from_box)
        self.thresholdSlider.valueChanged.connect(self._set_threshold_box_from_slider)
        self.thresholdBox.textEdited.connect(self._set_threshold_slider_from_box)

        self.volumeKnob.valueChanged.connect(self.gain_changed)
        self.thresholdSlider.valueChanged.connect(self.threshold_changed)
        self.triggerCheck.stateChanged.connect(lambda state: self.trigger_enabled_changed.emit(bool(state)))
        self.muteAudioCheck.stateChanged.connect(lambda state: self.mute_enabled_changed.emit(bool(state)))

        self.volumeKnob.valueChanged.connect(self._emit_settings_changed)
        self.gainBox.textEdited.connect(self._emit_settings_changed)
        self.thresholdSlider.valueChanged.connect(self._emit_settings_changed)
        self.thresholdBox.textEdited.connect(self._emit_settings_changed)
        self.triggerCheck.stateChanged.connect(self._emit_settings_changed)
        self.muteAudioCheck.stateChanged.connect(self._emit_settings_changed)


    def _emit_settings_changed(self):
        """Emits the general settings_changed signal if not blocked by programmatic changes."""
        if not self._is_programmatic_change:
            self.settings_changed.emit()

    def _set_threshold_slider_from_box(self):
        """Updates the threshold slider when the threshold QLineEdit is edited."""
        if self._is_programmatic_change: return
        try:
            value = int(self.thresholdBox.text())
            if 0 <= value <= 100:
                self._is_programmatic_change = True
                if self.thresholdSlider.value() != value:
                    self.thresholdSlider.setValue(value)
                self.thresholdBox.setStyleSheet("")
                self._is_programmatic_change = False
            else:
                self.thresholdBox.setStyleSheet("color: red;")
        except ValueError:
            self.thresholdBox.setStyleSheet("color: red;") 
        finally:
             if self._is_programmatic_change: self._is_programmatic_change = False

    def _set_threshold_box_from_slider(self, value):
        """Updates the threshold QLineEdit when the threshold QSlider is moved."""
        if self._is_programmatic_change: return
        self._is_programmatic_change = True
        value_str = str(value)
        if self.thresholdBox.text() != value_str:
            self.thresholdBox.setText(value_str)
            self.thresholdBox.setStyleSheet("")
        self._is_programmatic_change = False

    def _set_volume_knob_from_box(self):
        """Updates the volume QDial when the gain QLineEdit is edited."""
        if self._is_programmatic_change: return
        try:
            value = int(self.gainBox.text())
            if 0 <= value <= 100:
                self._is_programmatic_change = True
                if self.volumeKnob.value() != value:
                    self.volumeKnob.setValue(value)
                self.gainBox.setStyleSheet("") 
                self._is_programmatic_change = False
            else:
                self.gainBox.setStyleSheet("color: red;") 
        except ValueError:
            self.gainBox.setStyleSheet("color: red;") 
        finally:
            if self._is_programmatic_change: self._is_programmatic_change = False

    def _set_gain_box_from_knob(self, value):
        """Updates the gain QLineEdit when the volume QDial is turned."""
        if self._is_programmatic_change: return
        self._is_programmatic_change = True
        value_str = str(value)
        if self.gainBox.text() != value_str:
            self.gainBox.setText(value_str)
            self.gainBox.setStyleSheet("") 
        self._is_programmatic_change = False

    def get_config_values(self):
        """
        Returns the current state of the UI controls in this tab as a dictionary
        suitable for saving to the configuration file.
        """
        return {
            "gainBox": self.gainBox.text(),
            "thresholdBox": self.thresholdBox.text(),
            "triggerCheck": str(self.triggerCheck.isChecked()),
            "muteAudioCheck": str(self.muteAudioCheck.isChecked())
        }

    def set_values_from_dict(self, settings):
        """
        Applies settings from a dictionary to the UI controls in this tab.
        Typically used during initialization or when loading configuration.

        Args:
            settings (dict): A dictionary containing the values for the controls.
                             Keys should match those returned by get_config_values.
        """
        self._is_programmatic_change = True 
        try:
            # --- Set Gain/Volume ---
            gain_value_str = settings.get('gainBox', '100')
            self.gainBox.setText(gain_value_str)
            try:
                gain_value_int = int(gain_value_str)
                if 0 <= gain_value_int <= 100:
                    if self.volumeKnob.value() != gain_value_int:
                        self.volumeKnob.setValue(gain_value_int)
                    self.gainBox.setStyleSheet("")
                else:
                    self.gainBox.setStyleSheet("color: red;") 
                    if self.volumeKnob.value() != 100:
                        self.volumeKnob.setValue(100)
            except ValueError:
                self.gainBox.setStyleSheet("color: red;")
                if self.volumeKnob.value() != 100:
                    self.volumeKnob.setValue(100)


            # --- Set Threshold ---
            threshold_value_str = settings.get('thresholdBox', '50')
            self.thresholdBox.setText(threshold_value_str)
            try:
                threshold_value_int = int(threshold_value_str)
                if 0 <= threshold_value_int <= 100:
                    if self.thresholdSlider.value() != threshold_value_int:
                        self.thresholdSlider.setValue(threshold_value_int)
                    self.thresholdBox.setStyleSheet("") 
                else:
                    self.thresholdBox.setStyleSheet("color: red;")
                    if self.thresholdSlider.value() != 50:
                        self.thresholdSlider.setValue(50)
            except ValueError:
                self.thresholdBox.setStyleSheet("color: red;")
                if self.thresholdSlider.value() != 50:
                    self.thresholdSlider.setValue(50)

            # --- Set Checkboxes ---
            trigger_checked = settings.get('triggerCheck', 'True').lower() == 'true'
            self.triggerCheck.setChecked(trigger_checked)

            mute_checked = settings.get('muteAudioCheck', 'False').lower() == 'true'
            self.muteAudioCheck.setChecked(mute_checked)

        except Exception as e:
             print(f"Error applying settings to MainTab: {e}\n{traceback.format_exc()}")
        finally:
            self._is_programmatic_change = False 

    # --- Getters for current state ---
    def get_gain(self):
        """Returns the current gain value (0-100) from the volume knob."""
        return self.volumeKnob.value()

    def get_threshold(self):
        """Returns the current threshold value (0-100) from the slider."""
        return self.thresholdSlider.value()

    def is_trigger_enabled(self):
        """Returns True if the 'Enable Trigger' checkbox is checked, False otherwise."""
        return self.triggerCheck.isChecked()

    def is_mute_enabled(self):
        """Returns True if the 'Mute Audio Warning' checkbox is checked, False otherwise."""
        return self.muteAudioCheck.isChecked()

    # --- Method to update progress bar ---
    def update_volume_bar(self, level, threshold):
         """
         Updates the volume progress bar's value and changes its color based
         on whether the level exceeds the threshold.

         Args:
             level (int): The current volume level (0-100).
             threshold (int): The current trigger threshold (0-100).
         """
         level = max(0, min(level, 100))
         self.volumeBar.setValue(level)

         if level >= threshold:
             self.volumeBar.setStyleSheet(
                 """
                 QProgressBar { border: 1px solid grey; border-radius: 1px; text-align: center; }
                 QProgressBar::chunk { background-color: red; width: 1px; }
                 """
             )
         else:
             self.volumeBar.setStyleSheet(
                 """
                 QProgressBar { border: 1px solid grey; border-radius: 1px; text-align: center; }
                 QProgressBar::chunk { background-color: green; width: 1px; }
                 """
             )
