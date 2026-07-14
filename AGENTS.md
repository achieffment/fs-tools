# AGENTS.md

## Обзор

Памятка для агентов по репозиторию `fs-tools` — единый пакет четырёх CLI-утилит
(нормализация имён, проверка структуры, синхронизация с сервером, проверка схемы
базы знаний) с общим ядром.

## Роль

Кроссплатформенные правки (Windows/WSL/macOS/Linux) сохраняют контракты
(коды возврата, терминальный отчёт, текст веб-хука, формат `.fs-log.log`),
минимальный diff, следование локальным соглашениям (`.claude/rules/`).
Не переписывай модули «с нуля» и не навязывай архитектуру без запроса.

## Раскладка (src-layout)

```text
src/fs_tools/
├── shared/       # общий код всех режимов
├── normalizer/   # режим нормализации (rules/, cli_args.py, name.py, engine.py, ignore.py, safety.py, log.py, runner.py)
├── checker/      # режим проверки (rule.py, engine.py, report.py, notify.py, log.py, runner.py)
├── syncher/      # режим синхронизации ПК → сервер (cli_args.py, config.py, ignore.py, rsync.py, offload.py, report.py, notify.py, log.py, runner.py)
├── schemer/      # режим проверки схемы базы знаний, read-only (config.py, engine.py, report.py, notify.py, log.py, runner.py)
├── cli.py        # диспетчер fs-tools (ленивый импорт runner режима)
└── __main__.py   # python -m fs_tools
```

Состав каждого пакета по файлам с назначением — раздел «Распределение по
пакетам» в [`docs-consistency-matrix.md`](.claude/rules/docs-consistency-matrix.md)
(не дублируется здесь). Несимметрия `syncher`: у режима нет `engine.py`/`Fs*`-класса
и `safety.py` (структура — `cli_args`/`config`/`ignore`/`rsync`/`offload`/`report`);
врапнеры `log.py`/`runner.py` и раскладка тестов/примеров симметрию сохраняют.
`schemer` симметричен `normalizer`/`checker`: ядро — `engine.py` с классом `Fs*`
(`FsSchemer`), собственных CLI-флагов нет (`_build_parser()` не заводится).

Точки входа (`pyproject.toml [project.scripts]`): `fs-normalizer`, `fs-checker`,
`fs-syncher`, `fs-schemer`, `fs-tools` (диспетчер `<normalize|check|sync|scheme>`).

## Правила проекта

Правила продублированы для двух редакторов: Cursor (`.cursor/rules/*.mdc`) и
Claude Code (`.claude/rules/*.md`, точка входа — [`CLAUDE.md`](CLAUDE.md)).
Содержание синхронно (карта поддерживается синхронно с
[`rules-sync.md`](.claude/rules/rules-sync.md)).

| Cursor                                                                     | Claude                                                                   | Тема                                                                |
|----------------------------------------------------------------------------|--------------------------------------------------------------------------|---------------------------------------------------------------------|
| [agents-format.mdc](.cursor/rules/agents-format.mdc)                       | [agents-format.md](.claude/rules/agents-format.md)                       | **Формат:** канонический скелет AGENTS/CLAUDE и файла-правила       |
| [audit-governor.mdc](.cursor/rules/audit-governor.mdc)                     | [audit-governor.md](.claude/rules/audit-governor.md)                     | **Аудит:** единый контракт аудита правок и проекта                  |
| [collaboration-boundaries.mdc](.cursor/rules/collaboration-boundaries.mdc) | [collaboration-boundaries.md](.claude/rules/collaboration-boundaries.md) | **Границы:** поведение агента и стиль коммуникации                  |
| [comments-style.mdc](.cursor/rules/comments-style.mdc)                     | [comments-style.md](.claude/rules/comments-style.md)                     | **Комментарии:** стиль в коде, выравнивание docs/`*.toml`           |
| [config-format.mdc](.cursor/rules/config-format.mdc)                       | [config-format.md](.claude/rules/config-format.md)                       | **Конфиг:** формат и валидация `.fs-syn.toml` (`syncher`)           |
| [cross-platform-safety.mdc](.cursor/rules/cross-platform-safety.mdc)       | [cross-platform-safety.md](.claude/rules/cross-platform-safety.md)       | **Платформы:** кроссплатформенность и безопасность ФС               |
| [date-rule.mdc](.cursor/rules/date-rule.mdc)                               | [date-rule.md](.claude/rules/date-rule.md)                               | **DateRule:** осознанные допущения (`normalizer`)                   |
| [docs-consistency.mdc](.cursor/rules/docs-consistency.mdc)                 | [docs-consistency.md](.claude/rules/docs-consistency.md)                 | **Синхронизация:** код ↔ правила ↔ AGENTS/CLAUDE ↔ README           |
| [docs-consistency-matrix.mdc](.cursor/rules/docs-consistency-matrix.mdc)   | [docs-consistency-matrix.md](.claude/rules/docs-consistency-matrix.md)   | **Матрица:** тип изменения → код/тесты/docs; пакеты `src/fs_tools/` |
| [examples.mdc](.cursor/rules/examples.mdc)                                 | [examples.md](.claude/rules/examples.md)                                 | **Примеры:** формирование фикстур по режимам                        |
| [external-references.mdc](.cursor/rules/external-references.mdc)           | [external-references.md](.claude/rules/external-references.md)           | **Самодостаточность:** запрет ссылок на внешние проекты             |
| [imports.mdc](.cursor/rules/imports.mdc)                                   | [imports.md](.claude/rules/imports.md)                                   | **Импорты:** порядок (PEP 8 / isort)                                |
| [lazy-import-order.mdc](.cursor/rules/lazy-import-order.mdc)               | [lazy-import-order.md](.claude/rules/lazy-import-order.md)               | **Lazy-import:** порядок `importlib.import_module`-блоков           |
| [naming-symmetry.mdc](.cursor/rules/naming-symmetry.mdc)                   | [naming-symmetry.md](.claude/rules/naming-symmetry.md)                   | **Именование:** словарь замен и симметрия имён                      |
| [offload-safety.mdc](.cursor/rules/offload-safety.mdc)                     | [offload-safety.md](.claude/rules/offload-safety.md)                     | **Offload:** безопасность локального удаления (`syncher`)           |
| [path-matching.mdc](.cursor/rules/path-matching.mdc)                       | [path-matching.md](.claude/rules/path-matching.md)                       | **Фильтр `.fs-nrm`:** gitignore-семантика (`normalizer`)            |
| [readme-format.mdc](.cursor/rules/readme-format.mdc)                       | [readme-format.md](.claude/rules/readme-format.md)                       | **README:** формат вводной части (секция «Обзор»)                   |
| [rsync-mapping.mdc](.cursor/rules/rsync-mapping.mdc)                       | [rsync-mapping.md](.claude/rules/rsync-mapping.md)                       | **rsync:** трансляция include/exclude в фильтры (`syncher`)         |
| [rule-matching.mdc](.cursor/rules/rule-matching.mdc)                       | [rule-matching.md](.claude/rules/rule-matching.md)                       | **Семантика `.fs-chk`:** разворачивание и негативы (`checker`)      |
| [rules-sync.mdc](.cursor/rules/rules-sync.mdc)                             | [rules-sync.md](.claude/rules/rules-sync.md)                             | **Синхронизация правил:** карта `.mdc` ↔ `.md`                      |
| [scheme-format.mdc](.cursor/rules/scheme-format.mdc)                       | [scheme-format.md](.claude/rules/scheme-format.md)                       | **Схема:** формат `.fs-sch.toml` и модель движка `schemer`          |
| [testing.mdc](.cursor/rules/testing.mdc)                                   | [testing.md](.claude/rules/testing.md)                                   | **Тесты:** режимов, обязательные проверки, демо-инварианты          |

Перед правками в соответствующей области — прочитать релевантное правило.
Событийные процедуры (не файловый паттерн, а момент рабочего процесса) вынесены
в skills, а не в правила: [`audit-governor`](.claude/skills/audit-governor/SKILL.md),
[`commit-hygiene`](.claude/skills/commit-hygiene/SKILL.md) (перед `git commit`/`git push`),
[`release-notes`](.claude/skills/release-notes/SKILL.md) (при выпуске релиза GitHub);
Cursor-эквиваленты — в `.cursor/skills/`.

## Синхронизация с Claude

Проект поддерживает оба редактора: `.cursor/rules/*.mdc` (Cursor) и
`.claude/rules/*.md` (Claude Code, точка входа — [`CLAUDE.md`](CLAUDE.md))
содержат один и тот же канон. Синхронизация двусторонняя: Cursor → Claude и
Claude → Cursor — правка, начатая в любом из двух наборов, переносится в
парный в этом же шаге, не «потом» (см.
[`.claude/rules/rules-sync.md`](.claude/rules/rules-sync.md)).

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
7. **Test** — полный цикл: `pytest`, `pylint --persistent=n --recursive=y src tests/*`, `ruff check .`,
   `mypy --strict -p fs_tools`;
8. **Sync docs** — по матрице [`docs-consistency-matrix.md`](.claude/rules/docs-consistency-matrix.md):
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
- **Безопасность ФС**: инварианты переименования и журнала — см.
  [`cross-platform-safety.md`](.claude/rules/cross-platform-safety.md).
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
- **Синхронизация (`syncher`)**: однонаправленность ПК → сервер, коды возврата `0/1/2/3`
  (наихудший среди профилей) — delete-guard/offload-инварианты и артефакты, которые
  никогда не передаются, см. [`cross-platform-safety.md`](.claude/rules/cross-platform-safety.md)
  и [`offload-safety.md`](.claude/rules/offload-safety.md).
- **Проверка схемы (`schemer`)**: read-only, коды возврата `0/1/2` (без
  «предупреждения» — статус только `ok`/`error`). Подробности —
  [`scheme-format.md`](.claude/rules/scheme-format.md).
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
`test_safety.py`, `test_engine.py`, `test_ignore.py`, `test_log.py`, `test_report.py`
+ `rules/`, `test_cli_args.py`, `test_runner.py` у нормализатора; `test_engine.py`,
`test_rule.py`, `test_notify.py`, `test_examples.py`, `test_runner.py` у checker;
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
