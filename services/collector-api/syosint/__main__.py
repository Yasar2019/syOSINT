from pathlib import Path

import uvicorn

from .api import create_app


def main():
    root = Path(__file__).resolve().parents[3]
    directory = root / "private-data"
    directory.mkdir(mode=0o700, exist_ok=True)
    app = create_app(f"sqlite:///{directory / 'syosint.sqlite3'}", root / "pending-exports")
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
