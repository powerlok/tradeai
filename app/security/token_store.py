import json
import os
from typing import List

TOKENS_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'secrets', 'api_tokens.json')


def _ensure_dir():
    d = os.path.dirname(TOKENS_FILE)
    os.makedirs(d, exist_ok=True)


def load_tokens() -> List[str]:
    _ensure_dir()
    try:
        with open(TOKENS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return [str(x) for x in data]
    except FileNotFoundError:
        return []
    except Exception:
        return []
    return []


def save_tokens(tokens: List[str]) -> None:
    _ensure_dir()
    with open(TOKENS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tokens, f, indent=2)


def add_token(token: str) -> bool:
    tokens = load_tokens()
    if token in tokens:
        return False
    tokens.append(token)
    save_tokens(tokens)
    return True


def remove_token(token: str) -> bool:
    tokens = load_tokens()
    if token not in tokens:
        return False
    tokens = [t for t in tokens if t != token]
    save_tokens(tokens)
    return True
