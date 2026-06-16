# AGENTS.md — fs-syncher

## Роль агента

Высокоуровневый инженер Windows, Linux, WSL и macOS, эксперт Python. Любое решение
принимается с оглядкой на все четыре ОС и на идиоматичный, безопасный Python.

## О проекте

CLI односторонней синхронизации локального каталога с сервером (**ПК → сервер**) через
внешний `rsync` поверх SSH. Состав синхронизации задаётся декларативно в `.fs-sync.toml`
в корне каталога; путь к каталогу — позиционный аргумент (пригодно для cron/планировщика,
интерактивного выбора нет). Утилита — тонкая обёртка: читает и валидирует конфиг,
транслирует правила include/exclude в фильтры `rsync` (сопоставление путей выполняет
сам `rsync`), формирует и запускает `rsync`, разбирает итог, пишет журнал `.fs-log` и
при необходимости шлёт веб-хук.

Инварианты: данные текут только ПК → сервер; без offload-профиля локальные файлы не
удаляются; в offload локальное удаление/архивирование — только после подтверждённой
(verify) передачи; повторный прогон без изменений ничего не передаёт и не удаляет.

## Структура

    sync_fs.py                  точка входа; обёртки sync.sh/.command/.bat (авто-venv + pip)
    syncher/__init__.py         публичное API — импортировать только отсюда
    syncher/cli.py              аргументы (path, --profile, --all, --dry-run, --force-delete, --verbose), сценарий, коды возврата, запись .fs-log, веб-хук
    syncher/config.py           чтение/валидация .fs-sync.toml (tomllib/tomli), модель профилей
    syncher/ignore.py           трансляция include/exclude в фильтры rsync; безусловное авто-исключение артефактов
    syncher/rsync.py            сборка/запуск rsync, листинг точки (source_files/remote_object_count), разбор итога, delete-guard
    syncher/offload.py          backup-профиль: verify передачи → after_push (delete/archive/nothing)
    syncher/report.py           формат стартового заголовка и итогового отчёта
    syncher/log.py              журнал .fs-log (общий формат серии)
    syncher/notify.py           веб-хук (FSSYNC_WEBHOOK_*), fire-and-forget
    tests/                      pytest: test_config/test_ignore/test_rsync/test_offload/test_cli/test_report/test_log/test_notify/test_examples + conftest
    examples/                   запускаемая песочница (.fs-sync.toml + источник + локальные приёмники) + README

## Контракт

1. **Безопасность данных.** Однонаправленность (ПК → сервер). Без offload-профиля
   локальные файлы не удаляются. В offload удаление/архивирование — только для
   подтверждённо переданных файлов (частичный успех не трогает непереданное).
   Серверные удаления защищены delete-guard (порог по количеству/доле, код 3 без
   `--force-delete`). `remote_root` валидируется (не корень `/`).
2. **Авто-исключение артефактов.** `.fs-sync.toml`, `.fs-log`, `.env` никогда не
   передаются (иначе меняющийся `.fs-log` сломает идемпотентность).
3. **Консистентность всегда.** Код, тесты, `examples/` и документация меняются вместе
   (см. `.cursor/rules/consistency.mdc`).
4. **Трансляция правил.** Сопоставление путей выполняет сам `rsync` (своего матчера
   нет); фильтры строятся детерминированно, область offload берётся у rsync через
   `--list-only` (см. `.cursor/rules/rsync-mapping.mdc`).
5. **Кросс-платформенность.** Linux/WSL/macOS — нативно; Windows — через WSL/cwrsync.
   Пути для rsync — posix; источник всегда с завершающим `/`.
6. **Импорты — по PEP 8 (isort)**, не по использованию; правится `ruff check --fix`.
   Комментарии — кратко, объясняют неочевидное.

## Коды возврата

- `0` — успех (включая «изменений нет»).
- `1` — ошибка запуска (нет каталога/конфига, ошибка валидации, нет `rsync` или `ssh`
  для SSH-цели).
- `2` — `rsync`/offload завершились ошибкой.
- `3` — остановлено delete-guard. Итог прогона — наихудший код по шкале `0 < 2 < 3`.

## Команды

Инструменты ставятся в `.venv` (`.venv/bin/<tool>` или `python -m`). В PowerShell
`&&` не поддерживается — команды разделяй.

    python -m venv .venv
    source .venv/bin/activate    # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

    pytest                                 # тесты
    ruff check syncher tests               # линтер
    mypy --strict syncher sync_fs.py       # типы

Прогон на песочнице: `python sync_fs.py examples --dry-run` — итог обязан совпасть с
зафиксированным в `examples/README.md`.
