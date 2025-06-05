import sys
import numpy as np
import requests
import sounddevice as sd
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QTabWidget, QPushButton, QMessageBox, QApplication)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
import traceback
import time

# Import Setup Utilities
from appSetup import discover_audio_devices, load_initial_configuration

# Import Tabs
from tabs.mainTab import MainTab
from tabs.visualWarningTab import VisualWarningTab
from tabs.optionsTab import OptionsTab
import configHandler
import threading


class micMonitorWindow(QMainWindow):
    """
    Main application window for the Microphone Guardian.
    Manages UI, audio stream, configuration, and interactions between tabs.
    """
    warning_needed = pyqtSignal()
    volume_level_updated = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microphone Guardian")
        self.setGeometry(500, 120, 400, 300)

        # --- Internal State ---
        self.stream = None
        self._current_gain = 100
        self._current_threshold = 50 
        self._trigger_enabled = True
        self._mute_enabled = False
        self.samplerate = 44100 
        self.inputDevice = None
        self.outputDevice = None

        self._last_webhook_time = 0
        self._webhook_url = ""
        self._webhook_interval_enabled = False
        self._webhook_interval_seconds = 60

        # --- Device Discovery ---
        self.inputDevices, self.outputDevices, device_error = discover_audio_devices()
        if device_error:
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Audio Device Error", device_error))
            self.inputDevices = []
            self.outputDevices = []

        # --- Load Configuration ---
        self.config = load_initial_configuration() 
        initial_main_settings = self.config['main']
        initial_visual_settings = self.config['visual']
        initial_options_settings = self.config['options']
        initial_devices_settings = self.config['devices']
        status_message = self.config['status_message']

        # --- Instantiate Tab Widgets ---
        self.mainTab = MainTab(configData=initial_main_settings, parent=self)
        self.visualWarningTab = VisualWarningTab(
            targetWidget=self,
            configData=initial_visual_settings,
            parent=self
        )

        self.optionsTab = OptionsTab(
            config_options=initial_options_settings,
            config_devices=initial_devices_settings,
            parent=self
        )

        # --- Status Label ---
        self.feedbackLabel = QLabel(status_message)
        self.feedbackLabel.setFixedHeight(20)

        # --- Tabs Setup ---
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.mainTab, "Main")
        self.tab_widget.addTab(self.optionsTab, "Options")
        self.tab_widget.addTab(self.visualWarningTab, "Visual Warning")

        # --- Main Layout ---
        centralWidget = QWidget()
        centralLayout = QVBoxLayout(centralWidget)
        centralLayout.addWidget(self.tab_widget)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(self.feedbackLabel)
        buttonsLayout.addStretch()
        self.saveButton = QPushButton("Save Settings")
        self.cancelButton = QPushButton("Cancel Changes")
        self.saveButton.setEnabled(True)
        self.cancelButton.setEnabled(True)
        buttonsLayout.addWidget(self.saveButton)
        buttonsLayout.addWidget(self.cancelButton)
        centralLayout.addLayout(buttonsLayout)

        self.setCentralWidget(centralWidget)

        # --- Connections ---
        self.warning_needed.connect(self.handle_warning_trigger)
        self.volume_level_updated.connect(self._handle_volume_update)

        self.mainTab.gain_changed.connect(self._update_thread_safe_params)
        self.mainTab.threshold_changed.connect(self._update_thread_safe_params)
        self.mainTab.trigger_enabled_changed.connect(self._update_thread_safe_params)
        self.mainTab.mute_enabled_changed.connect(self._update_thread_safe_params)
        self.optionsTab.settingsChanged.connect(self._handle_options_tab_changed)
        self.saveButton.clicked.connect(self.updateConfigs)
        self.cancelButton.clicked.connect(self.retrieveConfigs)

        # --- Final Initialization ---
        self._update_thread_safe_params() 
        self._update_webhook_params() 

        # Start stream based on loaded config
        self.inputDevice = initial_devices_settings.get('inputDevice')
        self.outputDevice = initial_devices_settings.get('outputDevice')
        if self.inputDevice and self.inputDevices:
            self.restartInput()
        elif not self.inputDevices:
            self.feedbackLabel.setText("Status: No input devices found. Cannot start monitoring.")
        else:
            self.feedbackLabel.setText("Status: Select an input device in Options.")


    def _handle_options_tab_changed(self):
        """Handles the settingsChanged signal from the OptionsTab."""
        new_input_name = self.optionsTab.get_selected_input_device_name()
        new_output_name = self.optionsTab.get_selected_output_device_name()

        self._update_webhook_params()

        if new_input_name != self.inputDevice:
            print(f"Input device selection changed from '{self.inputDevice}' to '{new_input_name}'. Restarting stream.")
            self.inputDevice = new_input_name
            self.restartInput()
        elif new_output_name != self.outputDevice:
            print(f"Output device selection changed to '{new_output_name}'.")
            self.outputDevice = new_output_name


    def _update_webhook_params(self):
        """Reads webhook settings from OptionsTab and updates internal state."""
        opts, _ = self.optionsTab.get_config_values()
        self._webhook_url = opts.get('webhookUrl', '')
        self._webhook_interval_enabled = opts.get('enableWebhookInterval', 'False').lower() == 'true'
        try:
            self._webhook_interval_seconds = int(opts.get('webhookIntervalSeconds', 60))
        except ValueError:
            self._webhook_interval_seconds = 60


    def _update_status_label(self, message):
        """Slot to update the feedback label text."""
        self.feedbackLabel.setText(message)


    def updateConfigs(self):
        """
        Gathers current settings from all tabs and saves them using configHandler.
        """
        print("Gathering UI state for saving...")
        try:
            main_settings = self.mainTab.get_config_values()
            visual_settings = self.visualWarningTab.get_config_values()
            options_settings, devices_settings = self.optionsTab.get_config_values()

            devices_settings['inputDevice'] = self.inputDevice or ''
            devices_settings['outputDevice'] = self.outputDevice or ''

            current_settings = {
                "main": main_settings,
                "options": options_settings,
                "devices": devices_settings,
                "visual": visual_settings
            }
            _, message = configHandler.save_config(current_settings)
            self._update_status_label(message)
        except Exception as e:
            error_msg = f"Status: Error saving settings: {e}"
            print(f"Error gathering or saving settings: {e}\n{traceback.format_exc()}")
            self._update_status_label(error_msg)


    def retrieveConfigs(self):
        """
        Loads settings from the configuration file and re-applies them to the UI,
        effectively cancelling any unsaved user changes by recreating tabs.
        """
        print("Re-loading configuration (Cancel pressed)...")

        self.config = load_initial_configuration()
        initial_main_settings = self.config['main']
        initial_visual_settings = self.config['visual']
        initial_options_settings = self.config['options']
        initial_devices_settings = self.config['devices']
        status_message = self.config['status_message']
        self._update_status_label(status_message)

        if not self.config['load_ok']:
             print("Warning: Configuration file could not be read properly.")
        try:
            # --- Recreate MainTab ---
            self.mainTab.deleteLater()
            self.mainTab = MainTab(configData=initial_main_settings, parent=self)
            self.mainTab.gain_changed.connect(self._update_thread_safe_params)
            self.mainTab.threshold_changed.connect(self._update_thread_safe_params)
            self.mainTab.trigger_enabled_changed.connect(self._update_thread_safe_params)
            self.mainTab.mute_enabled_changed.connect(self._update_thread_safe_params)
            self.tab_widget.removeTab(self.tab_widget.indexOf(self.tab_widget.findChild(MainTab))) 
            self.tab_widget.insertTab(0, self.mainTab, "Main")

            # --- Recreate OptionsTab ---
            self.optionsTab.deleteLater()
            self.optionsTab = OptionsTab(
                config_options=initial_options_settings,
                config_devices=initial_devices_settings,
                parent=self
            )
            self.optionsTab.settingsChanged.connect(self._handle_options_tab_changed)
            self.tab_widget.removeTab(self.tab_widget.indexOf(self.tab_widget.findChild(OptionsTab)))
            self.tab_widget.insertTab(1, self.optionsTab, "Options")

            self.visualWarningTab.deleteLater()
            self.visualWarningTab = VisualWarningTab(
                targetWidget=self,
                configData=initial_visual_settings,
                parent=self
            )
            self.tab_widget.removeTab(self.tab_widget.indexOf(self.tab_widget.findChild(VisualWarningTab)))
            self.tab_widget.insertTab(2, self.visualWarningTab, "Visual Warning")

            self.tab_widget.setCurrentIndex(0)
            self._update_thread_safe_params()
            self._update_webhook_params()

            self.inputDevice = initial_devices_settings.get('input_device_name')
            self.outputDevice = initial_devices_settings.get('output_device_name')

            if self.inputDevice and self.inputDevices:
                 print("Reloading config, restarting input stream.")
                 self.restartInput()
            elif not self.inputDevices:
                 self.stop_stream()
                 self._update_status_label("Status: No input devices found. Cannot start monitoring.")
            else:
                 self.stop_stream()
                 self._update_status_label("Status: Select an input device in Options.")


            print("Finished re-loading configuration.")

        except Exception as e:
            error_msg = f"Status: Error applying reloaded settings: {e}"
            print(f"Error applying loaded settings (retrieveConfigs): {e}\n{traceback.format_exc()}")
            self._update_status_label(error_msg)


    def _find_device_index_by_name(self, device_name, device_list):
        """Finds the index of a device in a list by its name."""
        if not device_name or not device_list:
            return None
        for i, device in enumerate(device_list):
            if device.get('name') == device_name:
                return device.get('index')
        return None

    def _get_device_default_samplerate(self, device_index, kind='input'):
        """Queries a device for its default sample rate."""
        try:
            device_info = sd.query_devices(device=device_index, kind=kind)
            if device_info and isinstance(device_info, dict):
                rate = int(device_info.get('default_samplerate', 0))
                print(f"Device {device_index} default sample rate: {rate}")
                return rate if rate > 0 else None
        except Exception as e:
            print(f"Error querying sample rate for device {device_index}: {e}")
        return None


    def _update_thread_safe_params(self):
        """
        Updates internal copies of gain, threshold, trigger enable, mute enable.
        """
        self._current_gain = self.mainTab.get_gain()
        self._current_threshold = self.mainTab.get_threshold()
        self._trigger_enabled = self.mainTab.is_trigger_enabled()
        self._mute_enabled = self.mainTab.is_mute_enabled()


    def stop_stream(self):
        """Stops and closes the active audio input stream."""
        if self.stream:
            try:
                if self.stream.active:
                    self.stream.stop()
                self.stream.close()
                print("Audio stream stopped and closed.")
            except Exception as e:
                print(f"Warning: Error stopping/closing stream: {e}")
            finally:
                self.stream = None


    def restartInput(self):
        """
        Stops existing stream, finds device index by name, queries sample rate,
        and starts a new InputStream.
        """
        self.stop_stream()

        if not self.inputDevice:
             self._update_status_label("Status: Cannot start stream - No Input Device selected.")
             print("Stream start aborted: No input device name.")
             return

        device_index = self._find_device_index_by_name(self.inputDevice, self.inputDevices)

        if device_index is None:
            self._update_status_label(f"Status: Input device '{self.inputDevice}' not found.")
            print(f"Stream start aborted: Could not find index for device '{self.inputDevice}'.")
            return

        queried_samplerate = self._get_device_default_samplerate(device_index, kind='input')
        if queried_samplerate:
            self.samplerate = queried_samplerate
        elif self.samplerate <= 0:
            self.samplerate = 44100
            print(f"Warning: Could not query sample rate for device {device_index}. Using default {self.samplerate} Hz.")

        if self.samplerate <= 0:
            self._update_status_label("Status: Cannot start stream - Invalid Sample Rate.")
            print(f"Stream start aborted: Invalid sample rate ({self.samplerate}).")
            return

        try:
            print(f"Attempting to start input stream on device {device_index} ('{self.inputDevice}') with SR={self.samplerate}")

            sd.default.device = device_index
            print(f"Set sd.default.device input to: {device_index}")

            self.stream = sd.InputStream(
                callback=self.ListenToMic,
                samplerate=self.samplerate,
                device=device_index,
                dtype='float32'
            )
            self.stream.start()
            self._update_status_label(f"Status: Monitoring '{self.inputDevice}'")
            print("Input stream started successfully.")

        except sd.PortAudioError as pae:
            msg = f"Status: PortAudio Error starting stream - {pae}"
            self._update_status_label(msg)
            print(f"PortAudioError starting stream: {pae}")
            self.stream = None
        except ValueError as ve:
             msg = f"Status: Value Error starting stream - {ve}"
             self._update_status_label(msg)
             print(f"ValueError starting stream (invalid device index?): {ve}")
             self.stream = None
        except Exception as e:
            msg = f"Status: Error starting stream - {e}"
            self._update_status_label(msg)
            print(f"Error starting stream: {e}\n{traceback.format_exc()}")
            self.stream = None


    def ListenToMic(self, indata, frames, callback_time_info, status):
        """Audio callback function (executed in a separate thread)."""
        if status:
            if status.input_overflow: print("Warning: Input overflow", file=sys.stderr)
            if status.input_underflow: print("Warning: Input underflow", file=sys.stderr)

        try:
            gain_factor = self._current_gain / 100.0
            threshold_level = self._current_threshold
            is_trigger_on = self._trigger_enabled

            if indata is None or indata.size == 0:
                volume_rms = 0
            else:
                amplified_data = indata * gain_factor
                if amplified_data.size > 0:
                    volume_rms = np.sqrt(np.mean(np.square(amplified_data)))
                else:
                    volume_rms = 0

            scaling_factor = 300
            calculated_level = min(int(volume_rms * scaling_factor), 100)

            self.volume_level_updated.emit(calculated_level)

            if is_trigger_on and calculated_level >= threshold_level:
                self.warning_needed.emit()

                # --- Basic Webhook Logic ---
                if self._webhook_url:
                    now = time.monotonic()
                    should_send = True
                    if self._webhook_interval_enabled:
                        if now - self._last_webhook_time < self._webhook_interval_seconds:
                            should_send = False

                    if should_send:
                        self._last_webhook_time = now
                        thread = threading.Thread(target=self._send_webhook_request, args=(self._webhook_url,), daemon=True)
                        thread.start()
        except Exception as e:
            print(f"Error in ListenToMic callback: {e}\n{traceback.format_exc()}", file=sys.stderr)

    def _send_webhook_request(self, url):
        """Sends a GET request to the specified URL (runs in a separate thread)."""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            print(f"Webhook GET request sent successfully to {url}, Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending webhook GET request to {url}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error during webhook request to {url}: {e}", file=sys.stderr)

    def _handle_volume_update(self, level):
        """Updates the volume bar in the MainTab (GUI thread)."""
        self.mainTab.update_volume_bar(level, self._current_threshold)

    def handle_warning_trigger(self):
        """Handles visual and audio warnings (GUI thread)."""
        if not self._mute_enabled:
            amplitude = 0.5
            frequency = 440
            duration = 0.2

            if amplitude > 0 and duration > 0 and self.samplerate > 0 and frequency > 0:
                output_device_index = self._find_device_index_by_name(self.outputDevice, self.outputDevices)

                try:
                    t = np.linspace(0., duration, int(self.samplerate * duration), endpoint=False)
                    waveform = amplitude * np.sin(2. * np.pi * frequency * t, dtype=np.float32)
                    sd.play(waveform, self.samplerate, device=output_device_index, blocking=False)
                except Exception as e:
                    msg = f"Status: Audio Warning Error - {e}"
                    self._update_status_label(msg)
                    print(f"Error playing warning sound: {e}", file=sys.stderr)
            else:
                pass # Silently skip if parameters are invalid

        self.visualWarningTab.trigger()

    def closeEvent(self, event):
        """Handles the window closing event."""
        print("Closing application...")
        self.stop_stream()
        print("Cleanup finished.")
        event.accept()

if __name__ == "__main__":
    if hasattr(Qt.ApplicationAttribute, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    try:
        print("Starting Microphone Guardian...")
        app = QApplication(sys.argv)
        listenerWindow = micMonitorWindow()
        listenerWindow.show()
        exit_code = app.exec()
    except Exception as e:
        print(f"\nFATAL ERROR during application startup or execution: {e}")
        traceback.print_exc()
        try:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Icon.Critical)
            msgBox.setWindowTitle("Fatal Error")
            msgBox.setText(f"A fatal error occurred:\n{e}\n\nSee console for details.")
            msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
            msgBox.exec()
        except Exception as msg_e:
            print(f"Could not display error message box: {msg_e}")
        exit_code = 1
    finally:
        print(f"Exiting with code {exit_code if 'exit_code' in locals() else 1}.")
        sys.exit(exit_code if 'exit_code' in locals() else 1)