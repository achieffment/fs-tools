---
paths:
  - "tests/**"
  - "examples/**"
---

# Тесты режимов

> Claude-эквивалент [`.cursor/rules/testing.mdc`](../../.cursor/rules/testing.mdc). Применяется при работе с `tests/**`/`examples/**`.

Дополняет раздел «Тесты» в [AGENTS.md](../../AGENTS.md).

Раскладка тестов зеркалит пакет (файл `test_<module>.py` на модуль): нормализатор —
`test_name.py`, `test_safety.py`, `test_engine.py` (FsNormalizer e2e), `test_ignore.py`,
`test_log.py`, `test_report.py` (+ `rules/test_<rule>.py`, `test_cli_args.py`,
`test_runner.py`); checker — `test_engine.py`, `test_rule.py`, `test_log.py`,
`test_notify.py`, `test_examples.py`, `test_runner.py`; syncher —
`test_config.py`, `test_cli_args.py`, `test_ignore.py`, `test_rsync.py`,
`test_offload.py`, `test_report.py`, `test_runner.py`, `test_notify.py`,
`test_log.py`, `test_examples.py`; schemer — `test_config.py`, `test_engine.py`,
`test_report.py`, `test_log.py`, `test_notify.py`, `test_runner.py`,
`test_examples.py`. Режим запуска —
`--import-mode=importlib` (задан в `pyproject.toml`); одноимённые `test_engine.py` /
`test_ignore.py` / `test_log.py` / `test_runner.py` / `test_notify.py` сосуществуют
(importlib). Хак вставки корня в `sys.path` не нужен (src-layout + editable).

Каталоги тестов обязаны быть пакетами Python: в `tests/`, `tests/shared/`,
`tests/normalizer/`, `tests/normalizer/rules/`, `tests/checker/`, `tests/syncher/`,
`tests/schemer/` должен быть `__init__.py`. Новые тестовые подпапки создавай сразу с
`__init__.py`. Без этого `pylint` может обходить дерево неполно даже при `--recursive=y`.

- Корневой `tests/conftest.py` — только по-настоящему общие фикстуры: дерево
  `make_tree` (фабрика из списка путей в `tmp_path`). Мод-специфичные держатся в
  `conftest.py` подпапок: фабрика нормализатора `nn` (`build_normalizer`) —
  `tests/normalizer/conftest.py`; запись `.fs-chk` `write_rule` —
  `tests/checker/conftest.py`; `make_tree(base, paths)` (переопределяет общий под
  деревья источника/приёмника) + `write_config` — `tests/syncher/conftest.py`; запись
  `.fs-sch.toml` `write_scheme_toml` — `tests/schemer/conftest.py`. Маркер
  `requires_rsync` (skip без бинаря rsync) определяется локально в нуждающихся
  тест-файлах `syncher`.
- `tests/shared/test_picker.py` — один общий файл: выбор каталога не дублируется.
- `tests/shared/test_env.py` — доступ к единому `.env`: путь, загрузка в `os.environ`
  (`load_env`), приоритет «процесс > файл» (`override=False`), идемпотентность,
  упрочнение прав. `load_env` мутирует `os.environ`, поэтому autouse-фикстура сбрасывает
  `env._STATE["loaded"]` и восстанавливает окружение. Веб-хук-ключи проверяются у checker.
- `tests/shared/test_log.py` — общие механики журнала (метка времени, отступ, append,
  utf-8). Мод-специфичные строки журнала проверяются в мод-тестах: пары `old -> new`
  и «(изменений нет)» — у normalizer; пути и «(нарушений нет)» — у checker; маркеры
  `+`/`-`/`>>` и «(изменений нет)» — у syncher; строки нарушений и «(нарушений
  нет)» — у schemer.
- `tests/shared/test_notify.py` — общая логика веб-хука (`shared.notify`): чтение
  конфигурации из env, https-only, lazy `requests`, Bearer-заголовок, гашение
  сетевых ошибок.
- `tests/shared/test_rules_consistency.py` — автоматически проверяет инвариант
  [`rules-sync.md`](rules-sync.md): симметрия пар `.claude/rules/*.md` ↔
  `.cursor/rules/*.mdc`, идентичный (алфавитный) порядок правил в `CLAUDE.md`,
  таблице «Правила проекта» `AGENTS.md` и карте `rules-sync.md`, наличие
  blockquote-ссылки на парный `.mdc` и frontmatter в каждом `.mdc`. Это
  постоянный regression-барьер вместо ручной сверки на каждом аудите.

Обязательные виды проверки:

- **normalizer**: юнит-правила (`tests/normalizer/rules/test_<rule>.py`), пайплайн
  `name.py`, идемпотентность (`normalize(normalize(x)) == normalize(x)`),
  безопасность имени (`enforce_safe_component`), фильтр `.fs-nrm`,
  `FsNormalizer`, коды возврата `runner.main`.
- **checker**: парсинг `.fs-chk`, разворачивание правил, коды возврата, picker,
  веб-хук (мок сети), сбой сканирования `**`-обхода (`errlist`, `@pytest.mark.skipif`
  не-POSIX, через `chmod`).
- **schemer**: парсинг/валидация `.fs-sch.toml` (`SchemeConfigError`), классификация
  групповых/тематических узлов, все категории нарушений (F1–F15: обязательный файл,
  опциональный с контентом, пустая группа, файл вне групповой папки, контент-правило
  `line`/`text`), исключение `.fs-sch.toml` из loose-проверки, коды возврата,
  веб-хук (мок сети).
- **syncher**: парсинг/валидация `.fs-syn.toml` и коды `ConfigError`; трансляция
  include/exclude в фильтры rsync; разбор `--itemize-changes`/`--list-only`;
  delete-guard (пороги по количеству/доле, код 3); offload (verify → `after_push`,
  частичный успех); коды возврата `0/1/2/3` и «наихудший среди профилей»; «нет
  аргумента → интерактивный picker, аргумент-каталог минует диалог». Интеграционные тесты с реальным rsync —
  `@requires_rsync` (skip без бинаря).
- **Аргумент-каталог минует диалог** — для всех режимов; при отсутствии аргумента
  normalizer/checker/syncher/schemer используют интерактивный выбор каталога.
- **Веб-хук**: окружение процесса важнее `.env` (проверяется в `test_env.py`);
  checker/syncher/schemer-тесты проверяют ключи окружения и делегирование в
  `shared.notify`, а поведение отправки (https-only, lazy `requests`, заголовки,
  гашение ошибок) проверяется в `tests/shared/test_notify.py`.

Проверка (инструменты в `.venv`; в PowerShell `&&` не поддерживается):

    .venv/bin/python -m pytest -q
    .venv/bin/python -m pylint --persistent=n --recursive=y src tests/*
    .venv/bin/python -m ruff check .
    .venv/bin/python -m mypy --strict -p fs_tools

`pylint` запускаем без кэша (`--persistent=n`) и с рекурсивным discovery
(`--recursive=y`) всегда. Общий прогон выполняем по шаблону `src tests/*`, чтобы
проверялись все режимы тестов; все тестовые каталоги при этом должны быть пакетами
с `__init__.py`.
При любом расхождении между диагностикой IDE и общим прогоном обязателен
точечный запуск по проблемному файлу:

    .venv/bin/python -m pylint --persistent=n tests/path/to/file.py

Только после общего + точечного прогона разрешено фиксировать статус «ошибок нет».

Всё должно быть зелёным. Идемпотентность дополнительно проверяй на копии
`examples/normalizer/` (исходник под git не трогаем):

    cp -r examples/normalizer /tmp/ex && rm -f /tmp/ex/.fs-nrm
    .venv/bin/python -c "from pathlib import Path; from fs_tools.normalizer import \
    build_normalizer, FsNormalizer as F; r=Path('/tmp/ex'); \
    n=F(build_normalizer()); n.apply(r); print(n.apply(r))"

Второй прогон **ничего не переименовывает** — ожидаем `(0, 1)`: единственный
`skipped` — задокументированный конфликт `08-edge-cases/conflict`. Любое
`renamed > 0` на втором прогоне — регресс идемпотентности.

Демо-инвариант checker: прогон на `examples/checker/` даёт ровно ожидаемое число
нарушений (см. `examples/checker/README.md`).

Демо-инвариант syncher: `--dry-run` на `examples/syncher/` даёт зафиксированный итог
(см. `examples/syncher/README.md`; проверяется `test_examples.py`, skip без rsync).

Демо-инвариант schemer: прогон на `examples/schemer/` (конфиг с
`apply_root = "Warehouse"` перенаправляет обход в `examples/schemer/Warehouse/`)
даёт ровно ожидаемое число нарушений (см. `examples/schemer/README.md`).
