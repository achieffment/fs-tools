"""Совместимость с разными версиями pathspec: выбор фабрики gitignore-паттернов.

Изолированный version-shim: имя фабрики выбирается один раз (`_FACTORY`) и
переиспользуется обоими режимами (фильтр `.fs-nrm` нормализатора, негативы
`.fs-chk` проверки).
"""
from __future__ import annotations

from pathspec.util import lookup_pattern


def _factory_name() -> str:
    """Имя фабрики gitignore-паттернов, доступной в установленной pathspec.

    В новых версиях алиас 'gitwildmatch' объявлен устаревшим в пользу 'gitignore',
    а в pathspec<0.12-совместимых сборках есть только 'gitwildmatch'. Берём первое
    доступное, чтобы не привязываться к версии и не плодить DeprecationWarning.
    """
    for name in ("gitignore", "gitwildmatch"):
        try:
            lookup_pattern(name)
        except LookupError:
            continue
        return name
    return "gitwildmatch"


_FACTORY = _factory_name()
