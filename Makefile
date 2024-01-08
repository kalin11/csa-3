APPLICATION_NAME = csa-lab-3-last
CODE = $(APPLICATION_NAME) tests/golden
DEFAULT_OUTPUT = machine_code

TEST_ARGS = --verbosity=2 --showlocals --log-level=DEBUG

all: $(LISQ_COMPILED_FILES)

format:
	poetry run python -m isort $(CODE)
	poetry run python -m black $(CODE)

lint:
	poetry run python -m pylint $(CODE)

clean:
	rm -rf output

test:
	poetry run python -m pytest $(TEST_ARGS)

update-goldens:
	poetry run python -m pytest --update-goldens