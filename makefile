.RECIPEPREFIX = >

.PHONY: all test

all: test

test:
> python -m pytest
