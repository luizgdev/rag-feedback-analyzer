# Variables
IMAGE_NAME = rag-comcast-app
CONTAINER_NAME = rag-container

# --- DEVELOPMENT COMMANDS ---

install:
	@echo "📦 Installing dependencies with Poetry..."
	poetry install

test:
	@echo "🧪 Running Unit Tests..."
	poetry run pytest

ingest:
	@echo "🚀 Running Data Ingestion Pipeline..."
	poetry run python src/ingest_data.py

run:
	@echo "📡 Starting Streamlit App..."
	poetry run streamlit run src/app.py

# --- DOCKER COMMANDS ---

docker-build:
	@echo "🐳 Building Docker Image..."
	docker build -t $(IMAGE_NAME) .

docker-run:
	@echo "▶️ Running Docker Container..."
	# We mount the local .env and chroma_db_data to persist state and secrets
	docker run -d -p 8501:8501 \
		-v $(PWD)/chroma_db_data:/app/chroma_db_data \
		-v $(PWD)/.env:/app/.env \
		--name $(CONTAINER_NAME) \
		$(IMAGE_NAME)

docker-stop:
	@echo "🛑 Stopping Container..."
	docker stop $(CONTAINER_NAME) && docker rm $(CONTAINER_NAME)

docker-logs:
	docker logs -f $(CONTAINER_NAME)

# --- LINT ---
lint:
	@echo "🔍 Checking code style..."
	poetry run ruff check .

format:
	@echo "✨ Formatting code..."
	poetry run ruff format .
