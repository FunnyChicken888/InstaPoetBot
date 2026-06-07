import json
import os

CONFIG_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'config.json'))
EXAMPLE_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'config.json.example'))


def load_config() -> dict:
    path = CONFIG_PATH if os.path.exists(CONFIG_PATH) else EXAMPLE_PATH
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: dict):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
