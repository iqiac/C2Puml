# Project directories
SRC_DIR := src

# Configuration file
CONFIG_FILE := ${SRC_DIR}/pyproject.toml

# Main file
MAIN_FILE := ${SRC_DIR}/c2puml.py

.PHONY: all build format test lint clean

all: build format test lint

build:
	@echo "Translating C graphs..."
	@python3 ${MAIN_FILE}

format:
	@echo "Formatting Python files..."
	@black $(SRC_DIR) --config $(CONFIG_FILE)
	@isort $(SRC_DIR) --settings-file $(CONFIG_FILE)

test:
	@echo "Running tests..."
	@pytest $(SRC_DIR) --config-file $(CONFIG_FILE)

lint:
	@echo "Analyzing Python files..."
	@pylint $(SRC_DIR) --rcfile=$(CONFIG_FILE)

clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pyd" -delete
	@find . -type f -name "*.coverage" -delete
