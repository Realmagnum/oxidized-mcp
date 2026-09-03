FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

RUN pip install --no-cache-dir .

ENV OXIDIZED_CONFIG_PATH=/srv/oxidized/configs

EXPOSE 8080

CMD ["python", "-m", "src.server"]