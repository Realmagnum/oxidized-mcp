# Улучшения сверх исходного SPEC.md

Этот файл содержит расширения первоначального проекта. `SPEC.md` не изменяется.

## Реализованные улучшения

1. **Безопасная выдача конфигурации** — `get_device_config` редактирует вероятные secrets по умолчанию; полный текст требует `include_secrets=true`.
2. **Stable error envelope** — ошибки возвращаются как `{ok: false, error_code, message, details}`.
3. **Repository health tool** — `validate_repository` проверяет Git working tree, число устройств и нераспознанные vendor formats.
4. **Dedicated routing tool** — `get_device_routing`, поскольку routing присутствует среди сущностей Фазы 1.
5. **Freshness-only tool** — `get_device_freshness` возвращает обязательную дату и возраст без передачи конфига.
6. **Structured presence/absence search** — `search_across_devices` поддерживает `operator=equals|contains|present|absent|unrestricted` для вопросов из критериев приёмки.
7. **Fail-fast configuration** — путь, TTL, stale threshold, Git timeout и output limits валидируются Pydantic.
8. **Path containment** — чтение не может выйти за пределы смонтированного Git repository.
9. **Bounded Git execution** — subprocess timeout, ограничение regex/result count и информативные ошибки.
10. **Cache invalidation по файлу** — parsed cache использует TTL вместе с `mtime_ns` и размером файла.
11. **Secret-safe logging** — stdio protocol не загрязняется; диагностические сообщения идут в stderr без содержимого конфигов.
12. **Rootless Docker image** — runtime запускается не от root; Oxidized repository документирован как read-only mount.
13. **Стандартный Python package** — `src/oxidized_mcp/` и console command `oxidized-mcp`.
14. **Автоматический plugin discovery** — новый vendor добавляется отдельным модулем без изменения core registry.
15. **Machine-readable output schemas** — MCP tools возвращают компактные JSON-compatible dictionaries.

## Отложенное улучшение

После появления реальных sanitized fixtures добавить golden JSON snapshots для каждой модели и grammar coverage matrix по firmware families.
