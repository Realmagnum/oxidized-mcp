# Повторная оценка проекта

## Решение

Репозиторий и `SPEC.md` сохраняются. Первоначальный Python bootstrap заменяется рабочей реализацией в стандартном package layout `src/oxidized_mcp/`.

`SPEC.md` является неизменяемым исходным контрактом. Расширения сверх него документируются отдельно в `IMPROVEMENTS.md`.

## Что переиспользовано из mcp-switch-server

Родственный проект: `https://gitea.rmg7.com/magnum/mcp-switch-server`.

Полезные решения:

1. **Composition root** — MCP server получает уже валидированные зависимости, не открывает репозиторий при импорте модуля.
2. **Pydantic fail-fast configuration** — строгие границы значений и запрет неизвестных полей.
3. **MCPServer decorator API** — схемы инструментов строятся из Python type hints, а descriptions находятся рядом с реализацией.
4. **Единый error envelope** — стабильные `ok`, `error_code`, `message`, `details` вместо необработанных исключений.
5. **Secret-safe logging/output** — конфиги по умолчанию редактируются перед передачей агенту.
6. **CI quality gates** — tests, compileall, Ruff, Bandit, pip-audit и pip check.
7. **Console entry point** — сервер запускается установленной командой, а не зависит от cwd.

Не переносится:

- SSH/Telnet/SNMP-клиенты;
- policy для destructive-команд;
- allow-list сетевых устройств;
- audit операций изменения состояния.

`oxidized-mcp` читает только локальный Git working tree и не взаимодействует с устройствами.

## Почему старый bootstrap заменяется

- package layout и relative imports нерабочие;
- tests падали на collection;
- плагины состояли из `NotImplementedError`;
- skips маскировали отсутствие реализации;
- cache не использовался;
- vendor filter выдавал ложную маркировку;
- обязательный `config_date` допускал `null`;
- integration tests не вызывали MCP tools.

## Новая архитектура

- `OxidizedService` — use cases и стабильные response contracts;
- `GitReader` — единственная read-only граница Git/filesystem;
- `VendorPlugin` — path/content detection и нормализованный parsing;
- `PluginRegistry` — автоматическое обнаружение плагинов;
- `ParsedConfigCache` — TTL + invalidation по `mtime_ns` и размеру;
- `OxidizedMCPServer` — тонкий MCP adapter;
- `config.py` — fail-fast runtime settings.

## Ограничение приёмки

В репозитории находятся synthetic fixtures. Они пригодны для regression/bootstrap tests, но не заменяют требуемые `SPEC.md` реальные sanitized Oxidized backups. Финальная точность vendor grammar должна быть повторно подтверждена после добавления таких файлов.
