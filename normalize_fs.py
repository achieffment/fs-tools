#!/usr/bin/env python3
"""Точка входа: вся логика в пакете normalizer/.

Запуск: python3 normalize_fs.py [КАТАЛОГ]. Без аргумента каталог выбирается
интерактивно; с аргументом-каталогом диалог не открывается (режим запуска по
таймеру: cron/планировщик).
"""
import sys

from normalizer.cli import main

if __name__ == "__main__":
    sys.exit(main())
