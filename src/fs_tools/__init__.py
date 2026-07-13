"""Кросс-платформенные CLI-утилиты работы с файловой системой.

Четыре режима над общим внутренним пакетом `fs_tools.shared`:

- `fs_tools.normalizer` — рекурсивная нормализация имён файлов и папок;
- `fs_tools.checker` — проверка наличия путей по правилам `.fs-chk`;
- `fs_tools.syncher` — синхронизация с сервером по `.fs-syn.toml` (rsync);
- `fs_tools.schemer` — проверка схемы дерева по `.fs-sch.toml`.

Точки входа: команды `fs-normalizer`/`fs-checker`/`fs-syncher`/`fs-schemer`
и диспетчер `fs-tools <normalize|check|sync|scheme>`.
"""
from __future__ import annotations

__all__ = ["__version__"]

__version__ = "1.1.0"
