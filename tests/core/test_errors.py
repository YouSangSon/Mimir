from mimir.core.errors import FetchError, MimirError, NormalizationError


def test_error_hierarchy():
    assert issubclass(FetchError, MimirError)
    assert issubclass(NormalizationError, MimirError)
