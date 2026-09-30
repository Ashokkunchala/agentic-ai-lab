from pathlib import Path

def list_python_files(root: str = ".") -> list[str]:
    return sorted(str(path) for path in Path(root).rglob("*.py") if ".venv" not in path.parts)

def summarize_repository(root: str = ".") -> dict:
    files = list_python_files(root)
    return {"python_files": len(files), "examples": files[:10]}

if __name__ == "__main__":
    print(summarize_repository())
