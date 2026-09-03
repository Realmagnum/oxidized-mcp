# oxidized-mcp

Read-only MCP stdio server для структурированного поиска по текущим конфигурациям сетевых устройств в Git-репозитории Oxidized.

- **Исходный неизменяемый контракт:** [SPEC.md](SPEC.md)
- **Улучшения сверх ТЗ:** [IMPROVEMENTS.md](IMPROVEMENTS.md)
- **Повторная архитектурная оценка:** [docs/REASSESSMENT.md](docs/REASSESSMENT.md)
- **Оставшиеся production-задачи:** [BACKLOG.md](BACKLOG.md)

## Возможности

- Vendor plugins: D-Link, ELTEX, SNR
- Path → content vendor detection
- VLAN, ACL, NTP, SNMP, interfaces, routing, LLDP, static MAC, Voice VLAN, SSH
- Обязательные `config_date`, `config_age_hours`, `stale_warning`
- Parsed config cache: TTL + invalidation по `mtime_ns`/size
- `git grep` с timeout и лимитами
- Stable machine-readable errors
- Redaction вероятных secrets в полном конфиге по умолчанию
- Опциональная live-телеметрия Oxidized через loopback-only `GET /nodes.json`

## Установка

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Проверка

```bash
python -m pytest
python -m ruff check src tests
python -m bandit -q -r src
python -m build
```

## Запуск

```bash
export OXIDIZED_CONFIG_PATH=/srv/oxidized/configs
oxidized-mcp --check
oxidized-mcp
```

## OpenCode / MCP stdio

```json
{
  "mcp": {
    "oxidized": {
      "type": "local",
      "command": ["/path/to/venv/bin/oxidized-mcp"],
      "environment": {
        "OXIDIZED_CONFIG_PATH": "/srv/oxidized/configs",
        "OXIDIZED_REST_ENABLED": "true"
      }
    }
  }
}
```

Точный формат config может зависеть от версии OpenCode. Ключевое требование — запустить `oxidized-mcp` через stdio и передать `OXIDIZED_CONFIG_PATH`.

## Опциональный Oxidized REST

По умолчанию REST отключён: MCP читает только Git-витрину конфигураций. При `OXIDIZED_REST_ENABLED=true` появляется инструмент `list_oxidized_nodes`, который делает только `GET http://127.0.0.1:8888/nodes.json` и возвращает live-инвентарь с результатом последней попытки backup.

```bash
OXIDIZED_REST_ENABLED=true
OXIDIZED_REST_BASE_URL=http://127.0.0.1:8888
OXIDIZED_REST_TIMEOUT=3
OXIDIZED_REST_CACHE_TTL=30
```

- URL принимается только как loopback HTTP base URL; произвольные host, path и credentials отклоняются.
- В ответ не попадают Oxidized `vars`, чтобы не раскрывать credential-like inventory fields.
- REST-данные не объединяются с Git-инструментами: `status` последней попытки не является `config_date` или `stale_warning`.
- MCP не имеет и не вызывает `/node/next`, reload или другие mutation endpoints.

## Docker

```bash
docker build -t oxidized-mcp:0.2.0 .
docker run --rm -i \
  --read-only \
  --mount type=bind,src=/srv/oxidized/configs,dst=/srv/oxidized/configs,readonly \
  oxidized-mcp:0.2.0
```

`EXPOSE` отсутствует намеренно: transport — stdio, TCP listener не создаётся.

## MCP tools

Исходные инструменты Фазы 1:

- `list_devices`
- `get_device_config`
- `get_device_vlans`
- `get_device_acls`
- `get_device_ntp`
- `get_device_snmp`
- `get_device_interfaces`
- `get_device_lldp`
- `get_device_mac_table`
- `get_device_voice_vlan`
- `get_device_ssh`
- `search_across_devices`
- `raw_search`

Улучшения:

- `get_device_routing`
- `get_device_freshness`
- `validate_repository`
- operators `present`, `absent`, `unrestricted` в глобальном поиске
- `list_oxidized_nodes` при явном `OXIDIZED_REST_ENABLED=true`

## Важное ограничение fixtures

Текущие файлы `tests/fixtures/` являются synthetic regression fixtures из первоначального bootstrap. Код полностью исполняемый и тестируется на них, но production acceptance парсеров требует заменить/дополнить их реальными sanitized Oxidized backups разных моделей и firmware families, как требует `SPEC.md`.

## Добавление vendor

См. [docs/adding_new_vendor.md](docs/adding_new_vendor.md).
