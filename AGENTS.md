# AGENTS

Памятка для агентов по репозиторию `fs-tools` — единый пакет двух CLI-утилит
(нормализация имён и проверка структуры) с общим ядром.

## Раскладка (src-layout)

```text
src/fs_tools/
├── shared/          # общий код обоих режимов
│   ├── picker.py        # выбор каталога (Windows/WSL/macOS/терминал)
│   ├── pick_folder.ps1  # нативный диалог Windows (IFileOpenDialog), грузится через importlib.resources
│   ├── pathspec_compat.py  # _FACTORY: version-shim фабрики gitignore-паттернов
│   ├── env.py           # единый .env: load_env (load_dotenv, override=False), путь, chmod 600
│   ├── log.py           # единый журнал .fs-log (append_log)
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
├── cli.py           # диспетчер fs-tools (ленивый импорт runner режима)
└── __main__.py      # python -m fs_tools
```

Точки входа (`pyproject.toml [project.scripts]`): `fs-normalizer`, `fs-checker`, `fs-tools`.

## Команды

```bash
pip install -e ".[normalizer,checker,dev]"   # editable + оба extra + инструменты
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
- **Веб-хук**: окружение процесса важнее `.env`; URL обязан быть `https://`.
- **Консистентность**: изменение поведения синхронизирует код, тесты, примеры и
  документацию. Детали и осознанные допущения — в `.cursor/rules/`.

## Тесты

Раскладка зеркалит пакет — файл `test_<module>.py` на модуль (`test_name.py`,
`test_safety.py`, `test_engine.py`, `test_ignore.py`, `test_log.py` + `rules/`,
`test_runner.py` у нормализатора; `test_engine.py`, `test_rule.py`, ... у checker).
Фикстуры: `make_tree` (общая) — `tests/conftest.py`; `nn` —
`tests/normalizer/conftest.py`; `write_rule` — `tests/checker/conftest.py`.
Идемпотентность нормализатора проверяй на копии `examples/normalizer/` (исходник под
git не трогаем).

## Ограничения

- Не коммить в ветку `master`.
- `.env`, `.venv`, `.fs-log`, `dist/`, `build/` — в `.gitignore`, не коммить.
