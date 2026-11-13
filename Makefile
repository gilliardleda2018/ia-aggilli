.PHONY: up down logs status build install test

up:
	cd docker && docker compose up -d

down:
	cd docker && docker compose down

logs:
	cd docker && docker compose logs -f

status:
	cd docker && docker compose ps

build:
	cd docker && docker compose build

install:
	pip install -r requirements.txt

test:
	python -m pytest tests/ -v
