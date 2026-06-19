# AGENTS

Памятка для агентов по репозиторию `fs-tools` — единый пакет трёх CLI-утилит
(нормализация имён, проверка структуры, синхронизация с сервером) с общим ядром.

## Раскладка (src-layout)

```text
src/fs_tools/
├── shared/          # общий код всех режимов
│   ├── picker.py        # выбор каталога (Windows/WSL/macOS/терминал)
│   ├── pick_folder.ps1  # нативный диалог Windows (IFileOpenDialog), грузится через importlib.resources
│   ├── pathspec_compat.py  # _FACTORY: version-shim фабрики gitignore-паттернов
│   ├── env.py           # единый .env: load_env (load_dotenv, override=False), путь, chmod 600
│   ├── log.py           # единый журнал .fs-log (append_log)
│   ├── notify.py        # общая отправка веб-хуков (URL/tok по ключам, https-only, lazy requests)
│   └── cli.py           # общий разбор аргументов, resolve_root
├── normalizer/      # режим нормализации
│   ├── rules/           # правила (по файлу на правило) + __all__
│   ├── name.py          # конвейер (build_normalizer, NameNormalizer)
│   ├── engine.py        # обход и переименование (FsNormalizer, deepest-first)
│   ├── ignore.py        # фильтр .fs-ignore
│   ├── safety.py        # enforce_safe_component (имя — один компонент пути)
│   ├── log.py           # write_fs_log (обёртка над shared.log)
│   └── runner.py        # main/run
├── checker/         # режим проверки
│   ├── rule.py          # разбор .fs-check
│   ├── engine.py        # разворачивание правил, сбор нарушений
│   ├── report.py        # формат отчёта
│   ├── notify.py        # веб-хук (ленивый requests; .env грузит shared.env, читает os.environ)
│   ├── log.py           # write_fs_log (обёртка)
│   └── runner.py        # main/run
├── syncher/         # режим синхронизации (ПК → сервер через rsync)
│   ├── config.py        # чтение/валидация .fs-sync.toml (tomllib)
│   ├── ignore.py        # трансляция include/exclude в фильтры rsync
│   ├── rsync.py         # сборка/запуск rsync, листинг, delete-guard
│   ├── offload.py       # backup-профиль: verify → after_push
│   ├── report.py        # заголовок + итоговый отчёт по профилям
│   ├── notify.py        # веб-хук (FSSYN_*, ленивый requests, через shared.env)
│   ├── log.py           # write_fs_log (обёртка)
│   └── runner.py        # main(argv) + run(root, args)
├── cli.py           # диспетчер fs-tools (ленивый импорт runner режима)
└── __main__.py      # python -m fs_tools
```

Несимметрия `syncher`: у режима нет `engine.py`/`Fs*`-класса и `safety.py` (структура —
`config`/`ignore`/`rsync`/`offload`/`report`); врапнеры `log.py`/`runner.py` и раскладка
тестов/примеров симметрию сохраняют.

Точки входа (`pyproject.toml [project.scripts]`): `fs-normalizer`, `fs-checker`,
`fs-syncher`, `fs-tools` (диспетчер `<normalize|check|sync>`).

## Команды

```bash
pip install -e ".[normalizer,checker,syncher,dev]"  # editable + все extra + инструменты
.venv/bin/python -m pytest -q                # тесты (--import-mode=importlib задан в pyproject)
.venv/bin/python -m ruff check .             # линтер (исправление: ruff check --fix .)
.venv/bin/python -m mypy --strict -p fs_tools
.venv/bin/python -m build                    # sdist + wheel
```

В PowerShell `&&` не поддерживается — команды по одной.

## Ключевые принципы

- **Ленивые импорты — намеренные**: `unidecode`/`requests`/`python-dotenv` и runner
  режимов в диспетчере импортируются внутри функций, чтобы режим работал без чужого
  extra. Не поднимай их в шапку модуля.
- **Ресурсы и `.env` — не от `__file__`**: `pick_folder.ps1` грузится через
  `importlib.resources.files("fs_tools.shared")`; путь к `.env` (`shared.env`) — через
  `FS_TOOLS_HOME`/CWD. Иначе не найдётся в установленном wheel.
- **Безопасность ФС**: имя — один компонент пути (`enforce_safe_component`); без
  перезаписи `dest`; deepest-first; case-only через временное имя; `.fs-log` только
  append. Скрытые (на `.`) и корень не трогаем.
- **Веб-хук**: окружение процесса важнее `.env`; URL обязан быть `https://`. Ключи:
  `FSCHK_*` (проверка), `FSSYN_*` (синхронизация).
- **Синхронизация (`syncher`)**: однонаправленность ПК → сервер; единый источник истины
  сопоставления — сам `rsync` (своего матчера нет); offload удаляет/архивирует только
  подтверждённо переданное; delete-guard блокирует массовые удаления (код 3); артефакты
  (`.fs-sync.toml`, `.fs-log`, `.env`) не передаются никогда; коды возврата `0/1/2/3`
  (наихудший среди профилей). Внешние бинарники: `rsync` (обязателен), `ssh` (SSH-цели).
  Журнал пишется только в боевом прогоне (не в `--dry-run`).
- **Консистентность**: изменение поведения синхронизирует код, тесты, примеры и
  документацию. Детали и осознанные допущения — в `.cursor/rules/`.
- **Симметрия именования**: словарь замен и правило подбора симметричных локальных
  имён зафиксированы в `.cursor/rules/naming-symmetry.mdc` (включая исключения по
  stdlib-контрактам и публичным API).

## Тесты

Раскладка зеркалит пакет — файл `test_<module>.py` на модуль (`test_name.py`,
`test_safety.py`, `test_engine.py`, `test_ignore.py`, `test_log.py` + `rules/`,
`test_runner.py` у нормализатора; `test_engine.py`, `test_rule.py`, ... у checker;
`test_config.py`, `test_ignore.py`, `test_rsync.py`, `test_offload.py`, `test_report.py`,
`test_runner.py`, `test_notify.py`, `test_log.py`, `test_examples.py` у syncher).
Фикстуры: `make_tree` (общая) — `tests/conftest.py`; `nn` —
`tests/normalizer/conftest.py`; `write_rule` — `tests/checker/conftest.py`;
`make_tree(base, paths)` + `write_config` — `tests/syncher/conftest.py` (переопределяют
общий `make_tree` под деревья источника/приёмника). Интеграционные тесты `syncher`
помечены skip при отсутствии `rsync`. Идемпотентность нормализатора проверяй на копии
`examples/normalizer/` (исходник под git не трогаем); демо-инвариант `syncher` —
`examples/syncher/` `--dry-run`.

## Ограничения

- Не коммить в ветку `master`.
- `.env`, `.venv`, `.fs-log`, `dist/`, `build/` — в `.gitignore`, не коммить.
