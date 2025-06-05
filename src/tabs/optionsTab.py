import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox,
    QSpinBox, QPushButton, QMessageBox, QApplication, QLineEdit, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt
import sounddevice as sd
import appSetup


class OptionsTab(QWidget):
    """
    Configuration options for audio processing, devices, and webhooks.
    """
    settingsChanged = pyqtSignal()

    def __init__(self, config_options=None, config_devices=None, parent=None):
        super().__init__(parent)

        self.input_devices = []
        self.output_devices = []
        self.initial_config_options = config_options if config_options else {}
        self.initial_config_devices = config_devices if config_devices else {}

        self._discover_devices()

        layout = QVBoxLayout(self)

        # --- Audio Parameters ---
        params_layout = QVBoxLayout()
        params_layout.addWidget(QLabel("Audio Parameters:"))

        thresh_layout = QHBoxLayout()
        thresh_layout.addWidget(QLabel("Activation Threshold (dBFS):"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(-90.0, 0.0)
        self.threshold_spin.setSingleStep(1.0)
        self.threshold_spin.setDecimals(1)
        self.threshold_spin.setValue(float(self.initial_config_options.get('threshold', -30.0)))
        self.threshold_spin.valueChanged.connect(self.settingsChanged.emit)
        thresh_layout.addWidget(self.threshold_spin)
        thresh_layout.addStretch()
        params_layout.addLayout(thresh_layout)

        mon_int_layout = QHBoxLayout()
        mon_int_layout.addWidget(QLabel("Monitor Interval (ms):"))
        self.monitor_interval_spin = QSpinBox()
        self.monitor_interval_spin.setRange(50, 1000)
        self.monitor_interval_spin.setSingleStep(10)
        self.monitor_interval_spin.setValue(int(self.initial_config_options.get('monitor_interval_ms', 100)))
        self.monitor_interval_spin.valueChanged.connect(self.settingsChanged.emit) 
        mon_int_layout.addWidget(self.monitor_interval_spin)
        mon_int_layout.addStretch()
        params_layout.addLayout(mon_int_layout)

        silence_layout = QHBoxLayout()
        silence_layout.addWidget(QLabel("Silence Duration Threshold (ms):"))
        self.silence_duration_spin = QSpinBox()
        self.silence_duration_spin.setRange(100, 10000) 
        self.silence_duration_spin.setSingleStep(100)
        self.silence_duration_spin.setValue(int(self.initial_config_options.get('silence_duration_ms', 1000)))
        self.silence_duration_spin.valueChanged.connect(self.settingsChanged.emit)
        silence_layout.addWidget(self.silence_duration_spin)
        silence_layout.addStretch()
        params_layout.addLayout(silence_layout)

        layout.addLayout(params_layout)
        layout.addSpacing(15)

        # --- Webhook Settings ---
        webhook_layout = QVBoxLayout()

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("(OPTIONAL) Webhook URL (GET Request):"))
        self.webhook_url_edit = QLineEdit()
        self.webhook_url_edit.setPlaceholderText("http://example.com/notify?status=active")
        self.webhook_url_edit.setText(self.initial_config_options.get('webhookUrl', ''))
        self.webhook_url_edit.textChanged.connect(self.settingsChanged.emit)
        url_layout.addWidget(self.webhook_url_edit)
        webhook_layout.addLayout(url_layout)

        interval_layout = QHBoxLayout()
        self.webhook_interval_check = QCheckBox("Limit Webhook Interval:")
        initial_interval_enabled = self.initial_config_options.get('enableWebhookInterval', 'False').lower() == 'true'
        self.webhook_interval_check.setChecked(initial_interval_enabled)
        self.webhook_interval_check.stateChanged.connect(self._handle_interval_check_change)

        self.webhook_interval_spin = QSpinBox()
        self.webhook_interval_spin.setRange(1, 3600)
        self.webhook_interval_spin.setSuffix(" seconds")
        self.webhook_interval_spin.setValue(int(self.initial_config_options.get('webhookIntervalSeconds', 60)))
        self.webhook_interval_spin.setEnabled(initial_interval_enabled)
        self.webhook_interval_spin.valueChanged.connect(self.settingsChanged.emit)

        interval_layout.addWidget(self.webhook_interval_check)
        interval_layout.addWidget(self.webhook_interval_spin)
        interval_layout.addStretch()
        webhook_layout.addLayout(interval_layout)

        layout.addLayout(webhook_layout)
        layout.addSpacing(15)


        # --- Device Selection ---
        device_layout = QVBoxLayout()
        device_layout.addWidget(QLabel("Audio Devices:"))

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Input Device:"))
        self.input_combo = QComboBox()
        self._populate_device_combo(self.input_combo, self.input_devices, self.initial_config_devices.get('inputDevice', ''))
        self.input_combo.currentIndexChanged.connect(self.settingsChanged.emit)
        input_layout.addWidget(self.input_combo)
        device_layout.addLayout(input_layout)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Device:"))
        self.output_combo = QComboBox()
        self._populate_device_combo(self.output_combo, self.output_devices, self.initial_config_devices.get('outputDevice', ''))
        self.output_combo.currentIndexChanged.connect(self.settingsChanged.emit)
        output_layout.addWidget(self.output_combo)
        device_layout.addLayout(output_layout)

        self.refresh_button = QPushButton("Refresh Devices")
        self.refresh_button.clicked.connect(self._refresh_devices)
        device_layout.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignLeft)

        layout.addLayout(device_layout)

        layout.addStretch()


    def _handle_interval_check_change(self, state):
        """Enable/disable interval spinbox based on checkbox state and emit signal."""
        is_enabled = bool(state)
        self.webhook_interval_spin.setEnabled(is_enabled)
        self.settingsChanged.emit()

    def _discover_devices(self):
        """Discover audio devices using appSetup."""
        self.input_devices, self.output_devices, error = appSetup.discover_audio_devices()
        if error:
            QMessageBox.warning(self, "Device Error", f"Could not discover audio devices:\n{error}")

    def _populate_device_combo(self, combo, devices, selected_name):
        """Populates a QComboBox with device names and selects the one matching selected_name."""
        combo.clear()
        selected_list_index = -1 

        for i, device in enumerate(devices):
            combo.addItem(device['name'], i)
            print(f"  Adding item: '{device['name']}'")

            if device['name'] == selected_name:
                selected_list_index = i

        if selected_list_index != -1:
            combo_index_to_select = combo.findData(selected_list_index)
            if combo_index_to_select != -1:
                 print(f"  Setting current index to {combo_index_to_select} (data={selected_list_index})")
                 combo.setCurrentIndex(combo_index_to_select)
            else:
                 print(f"  Warning: Could not find combo box item with data {selected_list_index}, defaulting to index 0.")
                 if combo.count() > 0:
                     combo.setCurrentIndex(0)
        elif combo.count() > 0:
             combo.setCurrentIndex(0)

    def _refresh_devices(self):
        """Rediscover devices and repopulate combo boxes."""
        print("Refreshing audio devices...")
        current_input_name = self.get_selected_input_device_name()
        current_output_name = self.get_selected_output_device_name()

        self._discover_devices()

        self.input_combo.blockSignals(True)
        self.output_combo.blockSignals(True)

        self._populate_device_combo(self.input_combo, self.input_devices, current_input_name)
        self._populate_device_combo(self.output_combo, self.output_devices, current_output_name)

        self.input_combo.blockSignals(False)
        self.output_combo.blockSignals(False)


    def get_selected_input_device_name(self):
        """Returns the name of the selected input device."""
        index = self.input_combo.currentIndex()
        if index >= 0:
            device_index = self.input_combo.itemData(index)
            if 0 <= device_index < len(self.input_devices):
                return self.input_devices[device_index]['name']
        return None

    def get_selected_output_device_name(self):
        """Returns the name of the selected output device."""
        index = self.output_combo.currentIndex()
        if index >= 0:
            device_index = self.output_combo.itemData(index)
            if 0 <= device_index < len(self.output_devices):
                return self.output_devices[device_index]['name']
        return None

    def get_config_values(self):
        """Returns the current settings from the UI elements."""
        options = {
            'threshold': str(self.threshold_spin.value()),
            'monitor_interval_ms': str(self.monitor_interval_spin.value()),
            'silence_duration_ms': str(self.silence_duration_spin.value()),
            'webhookUrl': self.webhook_url_edit.text(),
            'enableWebhookInterval': str(self.webhook_interval_check.isChecked()),
            'webhookIntervalSeconds': str(self.webhook_interval_spin.value())
        }
        devices = {
            'inputDevice': self.get_selected_input_device_name() or '',
            'outputDevice': self.get_selected_output_device_name() or ''
        }
        return options, devices