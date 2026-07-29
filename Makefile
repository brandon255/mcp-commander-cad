.PHONY: install install-sw install-f360 install-mcp-commander test clean run-voice run-text

# Install all packages
install: install-sw install-f360 install-mcp-commander

install-sw:
	pip install -e packages/solidworks-mcp

install-f360:
	pip install -e packages/fusion360-mcp

install-mcp-commander:
	pip install -e packages/mcp-commander-agent

# Run MCP Commander
run-voice:
	mcp-commander --voice --debug

run-text:
	mcp-commander --text --debug

# Run MCP servers standalone (for testing)
run-sw-server:
	solidworks-mcp

run-f360-server:
	fusion360-mcp

# Testing
test:
	python -m pytest packages/ -v --tb=short

test-sw:
	python -m pytest packages/solidworks-mcp/ -v

test-f360:
	python -m pytest packages/fusion360-mcp/ -v

test-mcp-commander:
	python -m pytest packages/mcp-commander-agent/ -v

# Linting
lint:
	ruff check packages/

format:
	ruff format packages/

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf dist/ build/
