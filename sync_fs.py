#!/usr/bin/env python3
"""Точка входа: вся логика в пакете syncher/.

Запуск: python3 sync_fs.py [КАТАЛОГ] [ФЛАГИ]. Каталог — корень синхронизации с
файлом .fs-sync.toml; без аргумента берётся текущий рабочий каталог. Утилита
неинтерактивна и пригодна для запуска по таймеру (cron/планировщик).
"""
import sys

from syncher.cli import main

if __name__ == "__main__":
    sys.exit(main())
