FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y git \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 oxidized-mcp
COPY --from=builder /install /usr/local
USER oxidized-mcp
WORKDIR /home/oxidized-mcp

ENV OXIDIZED_CONFIG_PATH=/srv/oxidized/configs \
    PYTHONUNBUFFERED=1

CMD ["oxidized-mcp"]
