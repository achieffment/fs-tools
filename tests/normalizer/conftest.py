import pytest

from fs_tools.normalizer import build_normalizer
from fs_tools.normalizer.name import NameNormalizer


@pytest.fixture()
def nn() -> NameNormalizer:
    return build_normalizer()
