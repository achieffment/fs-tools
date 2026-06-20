"""Тесты барьера безопасности имени (safety.py): имя — один компонент пути.

Разделители/управляющие -> '-', запрещённые на Windows символы вырезаются.
"""
import pytest

from fs_tools.normalizer.safety import enforce_safe_component


@pytest.mark.parametrize(
    "bare, expected",
    [
        ("a/b", "a-b"),                          # '/' -> '-' (один компонент пути)
        ("a\\b", "a-b"),                         # '\' -> '-'
        ("a//b\\\\c", "a-b-c"),                  # цепочки разделителей схлопываются в один '-'
        ("a\x00b\x1fc", "a-b-c"),                # управляющие символы -> '-'
        ("a<b>c:d\"e|f?g*h", "abcdefgh"),         # запрещённые на Windows вырезаются
        ("<>:|?*", ""),                          # имя из одного «мусора» -> пусто
        ("clean_name-01", "clean_name-01"),      # безопасное имя не меняется (идемпотентность)
    ],
)
def test_enforce_safe_component(bare, expected):
    """Проверяет сценарий: enforce safe component."""
    assert enforce_safe_component(bare) == expected


@pytest.mark.parametrize("bare", ["a/b", "a\\b", "x<y>:\"|?*", "a\x00b", "<>:|?*"])
def test_enforce_safe_component_idempotent(bare):
    """Проверяет сценарий: enforce safe component idempotent."""
    once = enforce_safe_component(bare)
    assert enforce_safe_component(once) == once
