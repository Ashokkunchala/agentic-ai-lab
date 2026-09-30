import json
from pathlib import Path

MEMORY_FILE = Path(__file__).with_name("memory.json")

def load_memory() -> dict:
    if not MEMORY_FILE.exists():
        return {}
    return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))

def save_memory(memory: dict) -> None:
    MEMORY_FILE.write_text(json.dumps(memory, indent=2), encoding="utf-8")

if __name__ == "__main__":
    memory = load_memory()
    memory["last_lesson"] = "memory"
    memory["purpose"] = "persist useful facts beyond one turn"
    save_memory(memory)
    print(json.dumps(memory, indent=2))
