import sounddevice as sd
import configHandler
import traceback

def discover_audio_devices():
    """
    Queries the system for available audio input and output devices.

    Filters out system default devices to present a cleaner list to the user.

    Returns:
        tuple: A tuple containing:
            - list: A list of dictionaries representing input devices.
            - list: A list of dictionaries representing output devices.
            - str: An error message if discovery failed, otherwise None.
    """
    input_devices = []
    output_devices = []
    error_message = None
    try:
        all_devices = sd.query_devices()
        input_devices = [dev for dev in all_devices if dev["max_input_channels"] > 0 and 'sysdefault' not in dev['name'].lower()]
        output_devices = [dev for dev in all_devices if dev["max_output_channels"] > 0 and 'sysdefault' not in dev['name'].lower()]
        print(f"Discovered {len(input_devices)} input devices, {len(output_devices)} output devices.")
    except Exception as e:
        error_message = f"Could not query audio devices: {e}"
        print(f"Error during audio device discovery: {e}\n{traceback.format_exc()}")

    return input_devices, output_devices, error_message

def load_initial_configuration(config_path='config.ini'):
    """
    Loads the application configuration using configHandler.

    Parses the loaded settings into dictionaries for each application section/tab.

    Args:
        config_path (str, optional): Path to the configuration file.
                                     Defaults to configHandler.INI_FILENAME.

    Returns:
        dict: A dictionary containing:
            - 'main': Settings for the MainTab.
            - 'visual': Settings for the VisualWarningTab.
            - 'options': Settings for the OptionsTab (audio parameters).
            - 'devices': Settings for the OptionsTab (device selections).
            - 'status_message': A message indicating the result of loading the config.
            - 'load_ok': Boolean indicating if the config file was read successfully.
    """
    if config_path:
        loaded_data = configHandler.load_config(ini_path=config_path)
    else:
        loaded_data = configHandler.load_config()

    initial_settings = loaded_data.get('settings', {})
    status_message = loaded_data.get('message', 'Status: Error loading config.')
    load_ok = loaded_data.get('read_ok', False)

    config_bundle = {
        'main': initial_settings.get('main', {}),
        'visual': initial_settings.get('visual', {}),
        'options': initial_settings.get('options', {}),
        'devices': initial_settings.get('devices', {}),
        'status_message': status_message,
        'load_ok': load_ok
    }
    print(f"Configuration loaded: {status_message}")
    return config_bundle