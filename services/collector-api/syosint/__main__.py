import os
from pathlib import Path

import uvicorn

from .api import create_app


def main():
    root = Path(__file__).resolve().parents[3]
    database_path = Path(os.environ.get("SYOSINT_DB_PATH", str(root / "private-data/syosint.sqlite3")))
    directory = database_path.parent
    directory.mkdir(mode=0o700, exist_ok=True)
    app = create_app(f"sqlite:///{database_path}", Path(os.environ.get("SYOSINT_EXPORT_DIR", str(root / "pending-exports"))))
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
