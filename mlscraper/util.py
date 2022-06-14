from more_itertools import powerset


def powerset_max_length(candidates, length):
    return filter(lambda s: len(s) <= length, powerset(candidates))
