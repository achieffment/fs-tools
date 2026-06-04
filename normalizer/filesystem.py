"""Обход файловой системы и применение переименований."""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from .name import NameNormalizer


class FilesystemNormalizer:
    """Сбор путей (с обрезкой скрытых) и переименование deepest-first."""

    def __init__(self, normalizer: NameNormalizer):
        self.normalizer = normalizer

    @staticmethod
    def _hidden(name: str) -> bool:
        return name.startswith(".")

    def _collect(self, root: Path) -> list[Path]:
        items: list[Path] = []
        for dirpath, foldnames, filenames in os.walk(root, topdown=True, followlinks=False):
            base = Path(dirpath)
            # Обрезаем скрытые каталоги и файлы на месте, чтобы не заходить внутрь.
            foldnames[:] = [d for d in foldnames if not self._hidden(d)]
            filenames[:] = [f for f in filenames if not self._hidden(f)]
            for name in filenames:
                items.append(base / name)
            for name in foldnames:
                items.append(base / name)
        # Корневой каталог не добавляется (берём только его содержимое) -> не переименовывается.
        return items

    def apply(self, root: Path) -> tuple[int, int]:
        items = self._collect(root)
        # Самые вложенные — первыми: дети переименовываются раньше родителей.
        items.sort(key=lambda p: len(p.parts), reverse=True)
        renamed = 0
        skipped = 0
        for srcp in items:
            if not srcp.exists():
                skipped += 1
                continue
            name = self.normalizer.normalize(srcp.name, srcp.is_dir())
            if name == srcp.name:
                continue
            dest = srcp.parent / name
            case = srcp.name.casefold() == dest.name.casefold()
            try:
                # Конфликт — это занятость dest ДРУГИМ объектом. При case-only
                # переименовании на регистронезависимой ФС dest.exists() истинно,
                # но указывает на сам srcp (samefile), и конфликтом не является.
                if dest.exists() and not srcp.samefile(dest):
                    sys.stderr.write(f"Пропуск (конфликт): {srcp} -> {dest}\n")
                    skipped += 1
                    continue
                if case:
                    # На регистронезависимых ФС (Windows) — через временное имя.
                    temp = dest.parent / f".__normtmp_{uuid.uuid4().hex}"
                    os.rename(srcp, temp)
                    os.rename(temp, dest)
                else:
                    os.rename(srcp, dest)
                renamed += 1
            except OSError as exc:
                sys.stderr.write(f"Ошибка переименования {srcp} -> {dest}: {exc}\n")
                skipped += 1
        return renamed, skipped
