"""Базовый интерфейс правила нормализации."""
from __future__ import annotations

from abc import ABC, abstractmethod


class Rule(ABC):
    """Базовое правило: преобразует stem имени."""

    @abstractmethod
    def apply(self, stem: str, is_dir: bool) -> str:
        """Преобразовать stem имени и вернуть результат."""
        raise NotImplementedError
