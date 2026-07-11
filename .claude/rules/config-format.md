# Формат `.fs-sync.toml`

> Claude-эквивалент [`.cursor/rules/config-format.mdc`](../../.cursor/rules/config-format.mdc). Применяется при работе с `src/fs_tools/syncher/*`.

Конфиг лежит в корне синхронизируемого каталога (путь — позиционный аргумент CLI).
Разбор — стандартный `tomllib` (Python 3.11+). Модель — `syncher/config.py`.

## Секции

- `[defaults]` — значения по умолчанию для всех профилей.
- `[[sync]]` — профили зеркалирования (ПК → сервер, с зеркалированием удалений).
- `[[backup]]` — профили offload (выгрузка с последующим локальным удалением/архивом).

## Поля профиля

- `name` — уникальное имя (обязательно).
- `local_root` — путь относительно конфига или абсолютный (обязателен, должен
  существовать).
- `remote_root` — `user@host:/path`, `alias:/path` из `~/.ssh/config` или локальный
  путь (обязателен; локальный отсчитывается от каталога конфига).
- `exclude` / `include` — списки gitignore-подобных паттернов (см. `rsync-mapping.md`).
- `delete` — зеркалить удаления (дефолт: `true` для sync, `false` для backup).
- `dry_run` — дефолт `false`.
- `delete_threshold` (число, дефолт 100) и `delete_threshold_pct` (доля %, дефолт 25)
  — пороги delete-guard; `force_delete` (дефолт `false`) снимает защиту.
- Передача: `checksum`, `compress`, `partial_progress` (bool), `bwlimit` (строка),
  `ssh_opts` (список строк).
- Только `[[backup]]`: `after_push` (`delete`|`archive`|`nothing`, дефолт `nothing`),
  `verify` (bool, дефолт `true`), `archive_dir` (для `archive`; дефолт
  `<local_root>/../_fs-backup/<profile>/<YYYY-MM-DD>/`).

## Валидация → `ConfigError` (код возврата 1)

- Уникальность `name` среди всех профилей.
- `local_root` существует.
- `remote_root` непустой и безопасный: не корень `/`, непустой путь после `:`.
- `after_push` — корректный enum; типы полей соответствуют ожидаемым.
- Сообщение об ошибке указывает профиль и поле.

Поле профиля перекрывает одноимённое из `[defaults]`. Меняя набор полей или дефолты,
синхронизируй `config.py`, тесты, README и `examples/syncher/`.

Legacy-ключи TOML — внешний контракт утилиты. Внутренняя модель может использовать
свои имена (`source_path`/`target_path`/`backup_path`) и маппинг, но поведение `rsync`
и других библиотек остаётся штатным.
