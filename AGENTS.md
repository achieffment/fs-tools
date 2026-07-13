# AGENTS.md

## Обзор

Памятка для агентов по репозиторию `fs-tools` — единый пакет четырёх CLI-утилит
(нормализация имён, проверка структуры, синхронизация с сервером, проверка схемы
базы знаний) с общим ядром.

## Роль

Эксперт по кроссплатформенным Python CLI-утилитам работы с файловой системой
(Windows/WSL/macOS/Linux): точные правки с сохранением контрактов
(коды возврата, терминальный отчёт, текст веб-хука, формат `.fs-log.log`),
минимальный diff, следование локальным соглашениям (`.claude/rules/`).
Не переписывай модули «с нуля» и не навязывай архитектуру без запроса.

## Раскладка (src-layout)

```text
src/fs_tools/
├── shared/                   # общий код всех режимов
│   ├── picker.py             # выбор каталога (Windows/WSL/macOS/терминал)
│   ├── pick_folder.ps1       # нативный диалог Windows (IFileOpenDialog), грузится через importlib.resources
│   ├── pathspec_compat.py    # _FACTORY: version-shim фабрики gitignore-паттернов
│   ├── env.py                # единый .env: load_env (load_dotenv, override=False), путь, chmod 600
│   ├── log.py                # единый журнал .fs-log.log (append_log)
│   ├── notify.py             # общая отправка веб-хуков (URL/tok по ключам, https-only, lazy requests)
│   └── cli.py                # общий разбор аргументов, resolve_root, run_mode_main
├── normalizer/               # режим нормализации
│   ├── rules/                # правила (по файлу на правило) + __all__
│   ├── cli_args.py           # единое объявление normalizer-флагов и проброс argv для диспетчера/runner
│   ├── name.py               # конвейер (build_normalizer, NameNormalizer)
│   ├── engine.py             # обход и переименование (FsNormalizer, deepest-first)
│   ├── ignore.py             # фильтр .fs-nrm
│   ├── safety.py             # enforce_safe_component (имя — один компонент пути)
│   ├── log.py                # write_fs_log (обёртка над shared.log)
│   └── runner.py             # main/run
├── checker/                  # режим проверки
│   ├── rule.py               # разбор .fs-chk
│   ├── engine.py             # разворачивание правил, сбор нарушений
│   ├── report.py             # формат отчёта
│   ├── notify.py             # веб-хук (ленивый requests; .env грузит shared.env, читает os.environ)
│   ├── log.py                # write_fs_log (обёртка)
│   └── runner.py             # main/run
├── syncher/                  # режим синхронизации (ПК → сервер через rsync)
│   ├── config.py             # чтение/валидация .fs-syn.toml (tomllib)
│   ├── cli_args.py           # единое объявление sync-флагов и проброс argv для диспетчера/runner
│   ├── ignore.py             # трансляция include/exclude в фильтры rsync
│   ├── rsync.py              # сборка/запуск rsync, листинг, delete-guard
│   ├── offload.py            # backup-профиль: verify → after_push
│   ├── report.py             # заголовок + итоговый отчёт по профилям
│   ├── notify.py             # веб-хук (FSSYN_*, ленивый requests, через shared.env)
│   ├── log.py                # write_fs_log (обёртка)
│   └── runner.py             # main(argv) + run(root, args)
├── schemer/                  # режим проверки схемы базы знаний (read-only)
│   ├── config.py             # чтение/валидация .fs-sch.toml (tomllib): группы, group.file
│   ├── engine.py             # обход и сбор нарушений (FsSchemer, F1-F15)
│   ├── report.py             # формат отчёта и строк нарушений
│   ├── notify.py             # веб-хук (FSSCH_*, ленивый requests, через shared.env)
│   ├── log.py                # write_fs_log (обёртка)
│   └── runner.py             # main/run
├── cli.py                    # диспетчер fs-tools (ленивый импорт runner режима)
└── __main__.py               # python -m fs_tools
```

Несимметрия `syncher`: у режима нет `engine.py`/`Fs*`-класса и `safety.py` (структура —
`cli_args`/`config`/`ignore`/`rsync`/`offload`/`report`); врапнеры `log.py`/`runner.py`
и раскладка тестов/примеров симметрию сохраняют. `schemer` симметричен
`normalizer`/`checker`: ядро — `engine.py` с классом `Fs*` (`FsSchemer`), собственных
CLI-флагов нет (`_build_parser()` не заводится).

Точки входа (`pyproject.toml [project.scripts]`): `fs-normalizer`, `fs-checker`,
`fs-syncher`, `fs-schemer`, `fs-tools` (диспетчер `<normalize|check|sync|scheme>`).

## Правила проекта

Правила продублированы для двух редакторов: Cursor (`.cursor/rules/*.mdc`) и
Claude Code (`.claude/rules/*.md`, точка входа — [`CLAUDE.md`](CLAUDE.md)).
Содержание синхронно (карта поддерживается синхронно с
[`rules-sync.md`](.claude/rules/rules-sync.md)).

| Cursor                                                                     | Claude                                                                   | Тема                                                           |
|----------------------------------------------------------------------------|--------------------------------------------------------------------------|----------------------------------------------------------------|
| [agents-format.mdc](.cursor/rules/agents-format.mdc)                       | [agents-format.md](.claude/rules/agents-format.md)                       | **Формат:** канонический скелет AGENTS/CLAUDE и файла-правила  |
| [audit-governor.mdc](.cursor/rules/audit-governor.mdc)                     | [audit-governor.md](.claude/rules/audit-governor.md)                     | **Аудит:** единый контракт аудита правок и проекта             |
| [collaboration-boundaries.mdc](.cursor/rules/collaboration-boundaries.mdc) | [collaboration-boundaries.md](.claude/rules/collaboration-boundaries.md) | **Границы:** поведение агента и стиль коммуникации             |
| [comments-style.mdc](.cursor/rules/comments-style.mdc)                     | [comments-style.md](.claude/rules/comments-style.md)                     | **Комментарии:** стиль в коде, выравнивание docs/`*.toml`      |
| [commit-hygiene.mdc](.cursor/rules/commit-hygiene.mdc)                     | [commit-hygiene.md](.claude/rules/commit-hygiene.md)                     | **Коммиты:** секреты перед коммитом, стилистика сообщений      |
| [config-format.mdc](.cursor/rules/config-format.mdc)                       | [config-format.md](.claude/rules/config-format.md)                       | **Конфиг:** формат и валидация `.fs-syn.toml` (`syncher`)      |
| [cross-platform-safety.mdc](.cursor/rules/cross-platform-safety.mdc)       | [cross-platform-safety.md](.claude/rules/cross-platform-safety.md)       | **Платформы:** кроссплатформенность и безопасность ФС          |
| [date-rule.mdc](.cursor/rules/date-rule.mdc)                               | [date-rule.md](.claude/rules/date-rule.md)                               | **DateRule:** осознанные допущения (`normalizer`)              |
| [docs-consistency.mdc](.cursor/rules/docs-consistency.mdc)                 | [docs-consistency.md](.claude/rules/docs-consistency.md)                 | **Синхронизация:** код ↔ правила ↔ AGENTS/CLAUDE ↔ README      |
| [examples.mdc](.cursor/rules/examples.mdc)                                 | [examples.md](.claude/rules/examples.md)                                 | **Примеры:** формирование фикстур по режимам                   |
| [external-references.mdc](.cursor/rules/external-references.mdc)           | [external-references.md](.claude/rules/external-references.md)           | **Самодостаточность:** запрет ссылок на внешние проекты        |
| [imports.mdc](.cursor/rules/imports.mdc)                                   | [imports.md](.claude/rules/imports.md)                                   | **Импорты:** порядок (PEP 8 / isort)                           |
| [lazy-import-order.mdc](.cursor/rules/lazy-import-order.mdc)               | [lazy-import-order.md](.claude/rules/lazy-import-order.md)               | **Lazy-import:** порядок `importlib.import_module`-блоков      |
| [naming-symmetry.mdc](.cursor/rules/naming-symmetry.mdc)                   | [naming-symmetry.md](.claude/rules/naming-symmetry.md)                   | **Именование:** словарь замен и симметрия имён                 |
| [offload-safety.mdc](.cursor/rules/offload-safety.mdc)                     | [offload-safety.md](.claude/rules/offload-safety.md)                     | **Offload:** безопасность локального удаления (`syncher`)      |
| [path-matching.mdc](.cursor/rules/path-matching.mdc)                       | [path-matching.md](.claude/rules/path-matching.md)                       | **Фильтр `.fs-nrm`:** gitignore-семантика (`normalizer`)       |
| [readme-format.mdc](.cursor/rules/readme-format.mdc)                       | [readme-format.md](.claude/rules/readme-format.md)                       | **README:** формат вводной части (секция «Обзор»)              |
| [release-notes.mdc](.cursor/rules/release-notes.mdc)                       | [release-notes.md](.claude/rules/release-notes.md)                       | **Релизы:** формат названий и описаний релизов GitHub          |
| [rsync-mapping.mdc](.cursor/rules/rsync-mapping.mdc)                       | [rsync-mapping.md](.claude/rules/rsync-mapping.md)                       | **rsync:** трансляция include/exclude в фильтры (`syncher`)    |
| [rule-matching.mdc](.cursor/rules/rule-matching.mdc)                       | [rule-matching.md](.claude/rules/rule-matching.md)                       | **Семантика `.fs-chk`:** разворачивание и негативы (`checker`) |
| [rules-sync.mdc](.cursor/rules/rules-sync.mdc)                             | [rules-sync.md](.claude/rules/rules-sync.md)                             | **Синхронизация правил:** карта `.mdc` ↔ `.md`                 |
| [scheme-format.mdc](.cursor/rules/scheme-format.mdc)                       | [scheme-format.md](.claude/rules/scheme-format.md)                       | **Схема:** формат `.fs-sch.toml` и модель движка `schemer`     |
| [testing.mdc](.cursor/rules/testing.mdc)                                   | [testing.md](.claude/rules/testing.md)                                   | **Тесты:** режимов, обязательные проверки, демо-инварианты     |

Перед правками в соответствующей области — прочитать релевантное правило.

## Рабочий процесс

1. **Read first** — релевантное правило в `.claude/rules/`, затрагиваемые тесты
   и примеры;
2. **Design check** — SRP/DRY: нет ли уже похожей утилиты/правила, которое
   можно переиспользовать, вместо нового кода;
3. **Minimal diff** — без drive-by рефакторинга вне задачи;
4. **Match conventions** — симметрия имён ([`naming-symmetry.md`](.claude/rules/naming-symmetry.md)),
   паттерн `engine.py`/`Fs*` у normalizer/checker/schemer;
5. **Preserve contracts** — коды возврата `runner.main`, формат терминального
   отчёта (`Статус:`/`Сводка:`), текст веб-хука, формат `.fs-log.log`;
6. **Register** — новое правило normalizer регистрируется в `build_normalizer()`
   и ре-экспортируется в `rules/__init__.py`/`normalizer/__init__.py` (аналогичная
   точка регистрации — для расширений других режимов);
7. **Test** — полный цикл: `pytest`, `pylint --recursive=y src tests/*`, `ruff check .`,
   `mypy --strict -p fs_tools`;
8. **Sync docs** — по матрице [`docs-consistency.md`](.claude/rules/docs-consistency.md):
   правила (оба каталога) → `AGENTS.md`/`CLAUDE.md` → `README.md`.

## Команды

```bash
pip install -e ".[normalizer,checker,syncher,schemer,dev]"             # editable + все extra + инструменты
.venv/bin/python -m pytest -q                                          # тесты (--import-mode=importlib задан в pyproject)
.venv/bin/python -m pylint --persistent=n --recursive=y src tests/*    # Pylint: полный рекурсивный охват src + всех tests/*
.venv/bin/python -m ruff check .                                       # линтер (исправление: ruff check --fix .)
.venv/bin/python -m mypy --strict -p fs_tools
.venv/bin/python -m build                                              # sdist + wheel
```

В PowerShell `&&` не поддерживается — команды по одной.

## Ключевые принципы

- **Ленивые импорты — намеренные**: `unidecode`/`requests`/`python-dotenv` и runner
  режимов в диспетчере загружаются лениво (через `importlib` в обработчике/функции),
  чтобы режим работал без чужого extra. Не поднимай тяжёлые зависимости в шапку модуля.
- **Ресурсы и `.env` — не от `__file__`**: `pick_folder.ps1` грузится через
  `importlib.resources.files("fs_tools.shared")`; путь к `.env` (`shared.env`) — через
  `FS_TOOLS_HOME`/CWD. Иначе не найдётся в установленном wheel.
- **Безопасность ФС**: имя — один компонент пути (`enforce_safe_component`); без
  перезаписи `dest`; deepest-first; case-only через временное имя; `.fs-log.log` только
  append. Скрытые (на `.`) и корень не трогаем.
- **Нормализация (`normalizer`)**: `--dry-run` строит план без переименований;
  журнал `.fs-log.log` пишется и в `dry-run`, и в `production` как последовательность
  событий (`old -> new`, `(КОНФЛИКТ) ...`, `(ОШИБКА) ...`).
- **Dry-run и журналы (оба режима)**: `normalizer` и `syncher` в `--dry-run`
  дописывают `.fs-log.log` с режимом `dry-run` и планом действий.
- **Формат `.fs-log.log`**: заголовок каждого блока включает дату, строки
  `Инструмент: normalizer|checker|syncher|schemer`, `Режим: production|dry-run`,
  `Результат:` и далее список строк в исходном порядке событий.
- **Стиль runner-парсера**: если у режима есть свои флаги, используй
  `_build_parser()` (как в `syncher` и `normalizer`) и не выноси одноразовый
  `path_help` в отдельную константу.
- **Нейминг диспетчера**: в `fs_tools/cli.py` для normalizer-блока держи
  симметричную тройку `map_norm_argument` / `add_norm_argument` /
  `norm_argv_from_namespace`.
- **Веб-хук**: окружение процесса важнее `.env`; URL обязан быть `https://`. Ключи:
  `FSCHK_*` (проверка), `FSSYN_*` (синхронизация), `FSSCH_*` (проверка схемы).
- **Синхронизация (`syncher`)**: однонаправленность ПК → сервер; единый источник истины
  сопоставления — сам `rsync` (своего матчера нет); offload удаляет/архивирует только
  подтверждённо переданное; delete-guard блокирует массовые удаления (код 3); артефакты
  (`.fs-syn.toml`, `.fs-log.log`, `.env`) не передаются никогда; коды возврата `0/1/2/3`
  (наихудший среди профилей). Внешние бинарники: `rsync` (обязателен), `ssh` (SSH-цели).
  Журнал пишется в `production` и `dry-run` (с соответствующей меткой режима).
- **Проверка схемы (`schemer`)**: конфиг `.fs-sch.toml` читается из того же
  каталога, что и весь режим; read-only, дерево не мутирует. Групповая папка
  матчится по basename на любой глубине, регистрозависимо. Единый механизм
  `[[group.file]]` (`optional`) выражает и обязательность, и опциональный
  контент-контроль. Коды возврата `0/1/2` (без «предупреждения» — статус только
  `ok`/`error`). Подробности — `.claude/rules/scheme-format.md`.
- **Консистентность**: изменение поведения синхронизирует код, тесты, примеры и
  документацию. Детали и осознанные допущения — в правилах проекта (`.claude/rules/`
  для Claude Code; `.cursor/rules/` для Cursor).
- **Симметрия именования**: словарь замен и правило подбора симметричных локальных
  имён зафиксированы в `.claude/rules/naming-symmetry.md` (Cursor:
  `.cursor/rules/naming-symmetry.mdc`), включая исключения по stdlib-контрактам и
  публичным API.
- **Запрет `AugAssign/Add`**: инкрементальное сложение не используем; вместо него
  пишем явную форму `name = name + value`. Контроль закреплён тестом
  `tests/shared/test_no_augassign.py`.
- **Pylint-проверка без кэша**: основной прогон всегда через
  `.venv/bin/python -m pylint --persistent=n --recursive=y src tests/*`.
  Этот запуск обязателен: он покрывает `tests/*` полностью при условии, что
  тестовые подпапки оформлены как пакеты с `__init__.py`. Если IDE показывает
  ошибку, а общий прогон чистый, обязателен
  точечный запуск по файлу
  `.venv/bin/python -m pylint --persistent=n tests/path/to/file.py`; только после
  этого фиксируем статус «ошибок нет».

## Тесты

Раскладка зеркалит пакет — файл `test_<module>.py` на модуль (`test_name.py`,
`test_safety.py`, `test_engine.py`, `test_ignore.py`, `test_log.py` + `rules/`,
`test_runner.py` у нормализатора; `test_engine.py`, `test_rule.py`, ... у checker;
`test_config.py`, `test_cli_args.py`, `test_ignore.py`, `test_rsync.py`,
`test_offload.py`, `test_report.py`, `test_runner.py`, `test_notify.py`,
`test_log.py`, `test_examples.py` у syncher; `test_config.py`, `test_engine.py`,
`test_report.py`, `test_log.py`, `test_notify.py`, `test_runner.py`,
`test_examples.py` у schemer).
Каталоги тестов обязательны как пакеты: `tests/`, `tests/shared/`,
`tests/normalizer/`, `tests/normalizer/rules/`, `tests/checker/`, `tests/syncher/`,
`tests/schemer/` должны содержать `__init__.py`; новые тестовые подпапки создаются
только с ним.
Фикстуры: `make_tree` (общая) — `tests/conftest.py`; `nn` —
`tests/normalizer/conftest.py`; `write_rule` — `tests/checker/conftest.py`;
`make_tree(base, paths)` + `write_config` — `tests/syncher/conftest.py` (переопределяют
общий `make_tree` под деревья источника/приёмника); `write_scheme_toml` —
`tests/schemer/conftest.py`. Интеграционные тесты `syncher`
помечены skip при отсутствии `rsync`. Идемпотентность нормализатора проверяй на копии
`examples/normalizer/` (исходник под git не трогаем); демо-инвариант `syncher` —
`examples/syncher/` `--dry-run`; демо-инвариант `schemer` — `examples/schemer/`
(конфиг с `apply_root = "Warehouse"` перенаправляет обход в
`examples/schemer/Warehouse/`).

## Ограничения

- Не коммить в ветку `master`.
- `.env`, `.venv`, `.fs-log.log`, `dist/`, `build/` — в `.gitignore`, не коммить.

## Границы

Не угадывать при неясности, не коммитить/push без явной просьбы, не раздувать
scope, не трогать сторонние пакеты, не переформатировать вне задачи. Детали —
[`collaboration-boundaries.md`](.claude/rules/collaboration-boundaries.md)
(Cursor: [`collaboration-boundaries.mdc`](.cursor/rules/collaboration-boundaries.mdc)).

## Коммуникация

Язык пользователя или репозитория; кратко: что сделано, зачем и как проверено.
Детали — [`collaboration-boundaries.md`](.claude/rules/collaboration-boundaries.md).

## Аудит изменений и проекта

- Для аудитов использовать project skill `audit-governor` с режимами `audit changed` и
  `audit full`.
- Единый контракт аудита закреплён в skill `audit-governor`
  (Claude Code: `.claude/skills/audit-governor/`; Cursor: `.cursor/rules/audit-governor.mdc`);
  его требования обязательны при любом запросе аудита.
- В режиме `audit changed` проверять весь набор правок: staged/unstaged/untracked, все
  коммиты ветки от base (`main`/`master`) и итоговый diff; не ограничиваться последним
  коммитом.
- После правок по результатам аудита повторять полный цикл проверок до green:
  `.venv/bin/python -m pytest -q`,
  `.venv/bin/python -m pylint --persistent=n --recursive=y src tests/*`,
  `.venv/bin/python -m ruff check .`,
  `.venv/bin/python -m mypy --strict -p fs_tools`.
- Аудит обязателен по всем пластам: код, тесты, examples, docs, комментарии, rules и
  `AGENTS.md`.
