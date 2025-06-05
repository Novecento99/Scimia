import os
from configparser import ConfigParser, NoSectionError, NoOptionError

INI_FILENAME = "config.ini"

# --- Default Values ---
DEFAULTS = {
    "main": {
        "gainBox": "100",
        "thresholdBox": "50",
        "triggerCheck": "True",
        "muteAudioCheck": "False"
    },
    "options": {
        "frequencyBox": "440",
        "durationBox": "0.5",
        "sampleRateBox": "44100",
        "amplitudeBox": "0.5",
        "webhookUrl": "",
        "enableWebhookInterval": "False",
        "webhookIntervalSeconds": "60"
    },
    "devices": {
        "inputDevice": "",
        "outputDevice": ""
    },
    "visual": {
        "enableVisualCheck": "True",
        "flashDurationMs": "300"
    }
}

def _get_config_value(config, section, option):
    """Safely get value from ConfigParser, falling back to defaults."""
    try:
        return config.get(section, option)
    except (NoSectionError, NoOptionError):
        try:
            return DEFAULTS[section][option]
        except KeyError:
            print(f"Warning: Missing default and config value for [{section}] {option}")
            return "" 

def load_config(ini_path=INI_FILENAME):
    """
    Loads settings from the INI file, merging with defaults for missing values.

    Args:
        ini_path (str): Path to the configuration file.

    Returns:
        dict: A dictionary containing all settings, structured by section.
              Includes status info: 'read_ok' (bool), 'message' (str).
    """
    print(f"Attempting to load configuration from: {ini_path}")
    config = ConfigParser()
    loaded_settings = {'read_ok': False, 'message': ''}

    if os.path.exists(ini_path):
        try:
            read_files = config.read(ini_path)
            if read_files:
                loaded_settings['read_ok'] = True
                loaded_settings['message'] = f"Settings loaded from {ini_path}."
                print(f"Successfully read {ini_path}")
            else:
                loaded_settings['message'] = f"{ini_path} found but could not be parsed. Using defaults."
                print(f"Warning: {ini_path} found but config.read() returned empty.")
        except Exception as e:
            loaded_settings['message'] = f"Error reading {ini_path} ({e}). Using defaults."
            print(f"Error reading {ini_path}: {e}")
    else:
         loaded_settings['message'] = f"{ini_path} not found. Using default settings."
         print(f"{ini_path} not found, using defaults.")

    settings_dict = {}
    for section, options in DEFAULTS.items():
        settings_dict[section] = {}
        for option in options:
            settings_dict[section][option] = _get_config_value(config, section, option)

    loaded_settings['settings'] = settings_dict
    return loaded_settings

def save_config(settings_dict, ini_path=INI_FILENAME):
    """
    Saves the provided settings dictionary to the INI file.

    Args:
        settings_dict (dict): Dictionary containing the current settings,
                              structured by section (e.g., {'main': {'gainBox': '90'}, ...}).
        ini_path (str): Path to the configuration file.

    Returns:
        tuple: (bool, str) indicating success status and a message.
    """
    print(f"Attempting to save configuration to: {ini_path}")
    config = ConfigParser()

    for section, options in settings_dict.items():
        if not config.has_section(section):
            config.add_section(section)
        for option, value in options.items():
            config.set(section, option, str(value))

    try:
        with open(ini_path, "w") as f:
            config.write(f)
        message = "Settings saved."
        print(message)
        return True, message
    except IOError as e:
        message = f"Error saving config: {e}"
        print(message)
        return False, message
    except Exception as e:
        message = f"An unexpected error occurred during save: {e}"
        print(message)
        return False, message
