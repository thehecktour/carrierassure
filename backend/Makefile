# ===========================
# Makefile for Django REST Framework project
# ===========================

# Docker image name
IMAGE_NAME = carrier-api

# Application port
PORT = 8000

# ===========================
# Main commands
# ===========================

.PHONY: help build run stop clean test shell install local migrate

help:
	@echo "Available commands:"
	@echo "  make build        -> Build the Docker image"
	@echo "  make run          -> Run the Docker container"
	@echo "  make stop         -> Stop and remove the container"
	@echo "  make clean        -> Remove containers and Docker images"
	@echo "  make test         -> Run tests with pytest"
	@echo "  make shell        -> Start poetry shell"
	@echo "  make install      -> Install dependencies with Poetry"
	@echo "  make local        -> Run Django local development server"
	@echo "  make migrate      -> Run Django migrations inside the container"

# Build Docker image
build:
	podman build -t $(IMAGE_NAME) .

# Run container
run:
	podman run -d -p $(PORT):$(PORT) --name $(IMAGE_NAME) $(IMAGE_NAME)

# Stop container
stop:
	podman stop $(IMAGE_NAME) || true
	podman rm $(IMAGE_NAME) || true

# Clean containers and images
clean:
	podman stop $(IMAGE_NAME) || true
	podman rm $(IMAGE_NAME) || true
	podman rmi -f $(IMAGE_NAME) || true

# Start Poetry shell
shell:
	poetry shell

# Install dependencies with Poetry
install:
	poetry install

# Run local Django development server
local:
	poetry run python manage.py runserver 0.0.0.0:$(PORT)

# Run Django migrations inside container
migrate:
	podman exec -it $(IMAGE_NAME) poetry run python manage.py migrate

# Run tests with pytest
test:
	poetry run pytest -v --cov=src tests/