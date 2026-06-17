"""Кросс-платформенные CLI-утилиты работы с файловой системой.

Два режима над общим внутренним пакетом `fs_tools.shared`:

- `fs_tools.normalizer` — рекурсивная нормализация имён файлов и папок;
- `fs_tools.checker` — проверка наличия путей по правилам `.fs-check`.

Точки входа: команды `fs-normalizer`/`fs-checker` и диспетчер `fs-tools <normalize|check>`.
"""
from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
