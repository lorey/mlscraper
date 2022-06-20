from more_itertools import powerset


def powerset_max_length(candidates, length):
    return filter(lambda s: len(s) <= length, powerset(candidates))


def no_duplicates_generator_decorator(func):
    def inner(*args, **kwargs):
        seen = set()
        for item in func(*args, **kwargs):
            if item not in seen:
                yield item
                seen.add(item)

    return inner
