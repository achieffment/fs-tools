#!/usr/bin/env python3
"""Точка входа: вся логика в пакете normalizer/.

Запуск: python3 normalize_fs.py <путь>
"""
import sys

from normalizer.cli import main

if __name__ == "__main__":
    sys.exit(main())
