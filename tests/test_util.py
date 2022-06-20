from mlscraper.util import no_duplicates_generator_decorator


def test_no_duplicates_generator_decorator():
    @no_duplicates_generator_decorator
    def decorated_generator():
        yield from [1, 1, 2, 3, 3, 3]

    assert list(decorated_generator()) == [1, 2, 3]
