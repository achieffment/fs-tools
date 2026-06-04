import sys
from pathlib import Path

# Делаем normalize_fs.py импортируемым из тестов.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
