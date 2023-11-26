.PHONY: run_test uvicorn_run stop clean logs kill inspect_volumes del_volumes inspect_network migrate revision history-migrations current sql-check downgrade help

include .env

VOLUMES = fastapi_proj_db_data fastapi_proj_cache_data fastapi_proj_test_db_data

# Run services
run_test:
	docker compose -f compose_test.yml up -d && sleep 10 && alembic upgrade head && docker compose -f compose_test.yml logs --follow

uvicorn_run:
	python app/main.py

# Stop services
stop:
	docker compose -f compose_test.yml down

# Clean system
clean:
	docker system prune

# Logging containers
logs:
	docker compose -f compose_test.yml logs --follow

# Kill services
kill:
	docker compose kill

inspect_volumes:
	@for volume in $(VOLUMES); do \
		echo ""; \
		docker volume inspect -f "Name: {{.Name}}" $$volume; \
		docker volume inspect -f "Mountpoint: {{.Mountpoint}}" $$volume; \
		docker volume inspect -f "CreatedAt: {{.CreatedAt}}" $$volume; \
		echo ""; \
	done

# Remove all volumes
del_volumes:
	docker volume prune --all

# Show network
inspect_network:
	@docker network inspect -v fastapi_proj_xhost

# Alembic make migrate
revision:
	alembic revision --autogenerate -m "$(name)"

# Alembic upgrade
migrate:
	alembic upgrade head

# Alembic check
history-migrations:
	alembic history

# Show current migration
current:
	alembic current

# Alembic test
sql-check:
	alembic upgrade --sql head

# Alembic downgrade
downgrade:
	alembic downgrade -1

# Generate fake contacts
fake_contacts:
	python app/source/services/faker_contacts.py

# Show help
help:
	@echo ""
	@echo "run_test - Docker Compose test up + watch"
	@echo "run_uvicorn - Run uvicorn server"
	@echo "stop - Docker Compose down"
	@echo "clean - Docker clean system"
	@echo "logs - Logging services"
	@echo "kill - Kill all containers"
	@echo "inspect_volumes - Inspect volumes"
	@echo "del_volumes - Warning! This command remove all volumes!"
	@echo "inspect_network - Inspect network"
	@echo 'revision name="name_revision" - Generate alembic revision'
	@echo "migrate - Apply Alembic migrations"
	@echo "history-migrations - Check Alembic migrations"
	@echo "current - Show current migration"
	@echo "sql-check - Generate SQL script migrations"
	@echo "downgrade - Downgrade migrations"
	@echo "fake_contacts - Generate fake contacts for database for user ID"
	@echo ""