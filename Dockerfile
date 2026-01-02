# 1. Base Image (Lightweight Python)
FROM python:3.11-slim

# 2. Environment Variables
# Prevents Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

# 3. Set Working Directory
WORKDIR /app

# 4. Install System Dependencies
# build-essential and curl are often needed for compiling certain python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Poetry
RUN pip install poetry

# 6. Copy Dependency Definitions
COPY pyproject.toml poetry.lock ./

# 7. Install Dependencies
# We disable virtualenv creation because Docker itself provides isolation
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# 8. Copy Application Code
COPY src/ src/

# 9. Expose Streamlit Port
EXPOSE 8501

# 10. Default Command
# We bind to 0.0.0.0 to make it accessible outside the container
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
