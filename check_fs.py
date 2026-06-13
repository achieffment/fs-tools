#!/usr/bin/env python3
"""Точка входа: вся логика в пакете checker/.

Запуск: python3 check_fs.py [КАТАЛОГ]. Без аргумента каталог выбирается
интерактивно; аргумент-каталог минует диалог (режим запуска по таймеру).
"""
import sys

from checker.cli import main

if __name__ == "__main__":
    sys.exit(main())
