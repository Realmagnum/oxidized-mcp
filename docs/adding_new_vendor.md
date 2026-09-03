# Добавление нового vendor plugin

## Контракт

Каждый plugin наследует `VendorPlugin` или `ClassicCLIPlugin`, задаёт уникальный `name`, path/content signatures и возвращает единый `DeviceConfig`.

```python
from oxidized_mcp.plugins.base import ClassicCLIPlugin


class CiscoPlugin(ClassicCLIPlugin):
    name = "cisco"
    path_patterns = ("/cisco/", "ios-")
    content_patterns = (r"^version 17\.", r"^interface GigabitEthernet")
```

Если общий classic CLI parser не покрывает синтаксис, переопределите `parse_config()` или отдельный `extract_*()`.

## Порядок

1. Добавьте минимум 2–3 **реальных sanitized Oxidized backup** разных моделей в `tests/fixtures/<vendor>/`.
2. Добавьте `src/oxidized_mcp/plugins/<vendor>.py`.
3. Добавьте path signatures и достаточно уникальные content signatures.
4. Реализуйте/переопределите извлечение всех сущностей Фазы 1.
5. Добавьте точные expected assertions или golden JSON snapshots.
6. Запустите полный quality gate.

Ручная регистрация не нужна: `PluginRegistry` автоматически загружает классы plugin из отдельных модулей.

## Обязательный checklist

- [ ] Path detection не конфликтует с существующими plugins.
- [ ] Content detection работает при нейтральном имени файла.
- [ ] VLAN: ID/name/tagged/untagged ports.
- [ ] Voice VLAN: ID/mode/ports/priority.
- [ ] ACL: name/rules/direction/bound ports.
- [ ] NTP: address/source.
- [ ] SNMP: community/user/host/version/access.
- [ ] Interface: name/description/enabled/VLAN/port-security.
- [ ] Routing: static/default routes.
- [ ] LLDP: global/timers/ports.
- [ ] Static MAC: MAC/VLAN/port.
- [ ] SSH: enabled/version/users/keys/ACL.
- [ ] Неизвестный синтаксис не преобразуется в выдуманное значение.
- [ ] Тесты не используют `skip` или `NotImplementedError` для требований Фазы 1.

## Запуск проверок

```bash
python -m pytest
python -m ruff check src tests
python -m bandit -q -r src
python -m build
```

## Приоритетные кандидаты

- Cisco IOS/IOS-XE
- Huawei VRP
- Juniper Junos — потребуется отдельный hierarchical parser
- MikroTik RouterOS — потребуется parser формата `/export`
