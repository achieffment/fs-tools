# Checklist: audit-governor

## Contents

- Источники истины
- Область аудита
- Обязательные проверки качества
- Обязательные команды
- Цикл выполнения
- Definition of Done

## Источники истины

- `AGENTS.md`
- `README.md`
- `examples/README.md`
- `examples/checker/README.md`
- `examples/normalizer/README.md`
- `examples/syncher/README.md`
- `examples/schemer/README.md`
- `pyproject.toml`
- `CLAUDE.md` (корневой: индекс со ссылками на `.claude/rules/*.md`,
  `@`-импорт `AGENTS.md`)
- `.claude/rules/*.md` (22 файла — 1:1 адаптация `.cursor/rules/*.mdc`):
  `agents-format.md`, `audit-governor.md`, `collaboration-boundaries.md`,
  `comments-style.md`, `config-format.md`, `cross-platform-safety.md`,
  `date-rule.md`, `docs-consistency.md`, `docs-consistency-matrix.md`,
  `examples.md`, `external-references.md`, `imports.md`,
  `lazy-import-order.md`, `naming-symmetry.md`, `offload-safety.md`,
  `path-matching.md`, `readme-format.md`, `rsync-mapping.md`,
  `rule-matching.md`, `rules-sync.md`, `scheme-format.md`, `testing.md`
- `.claude/skills/*/SKILL.md` — событийные процедуры вне файлового паттерна:
  `commit-hygiene` (перед `git commit`/`git push`), `release-notes` (при
  выпуске релиза GitHub)

## Область аудита

### Режим `audit changed`

- Проверить `git status` (staged, unstaged, untracked).
- Определить base-ветку (`main` или `master`).
- Проверить все коммиты текущей ветки относительно base.
- Проверить итоговый diff ветки относительно base.

### Режим `audit full`

- Проверить все ключевые модули в `src/fs_tools/`.
- Проверить все тесты в `tests/`.
- Проверить документацию и examples.
- Проверить правила (`CLAUDE.md` + `.claude/rules/*.md`) и агентные инструкции.

## Обязательные проверки качества

- Покрыть все пласты без исключений: код, тесты, examples, docs,
  комментарии, rules, agent guide.
- Подтвердить высокий инженерный уровень: SRP, DRY, минимализм, простота,
  читаемость.
- Консистентность кода, тестов, examples, docs, rules.
- Кроссплатформенность и безопасность.
- Комментарии: минимум, актуальность, выравнивание по
  `.claude/rules/comments-style.md`.
- Проверить автоконтроль выравнивания inline-комментариев:
  `tests/shared/test_markdown_comments.py` (командные fenced-блоки Markdown) и
  `tests/shared/test_toml_comments.py` (файлы `*.toml`) проходят в составе
  `pytest`; оба считают по локальным подблокам (между пустыми строками), но с
  разными профилями опорной колонки — точные параметры в
  `.claude/rules/comments-style.md`.
- Проверить, что `tests/shared/test_rules_consistency.py` проходит в составе
  `pytest`: симметрия пар `.claude/rules/*.md` ↔ `.cursor/rules/*.mdc`,
  идентичный порядок правил в `CLAUDE.md`/`AGENTS.md`/`rules-sync.md`,
  blockquote-ссылка и frontmatter в каждом файле-правиле (см.
  `.claude/rules/rules-sync.md`) — это регрессионный барьер именно от того
  типа расхождений, которые ранее находились только вручную на разных
  прогонах аудита.
- Проверить локальные naming-пары:
  - `src_rel/dst_rel` в `normalizer/engine.py`;
  - `map_norm_argument/add_norm_argument/norm_argv_from_namespace` в
    `fs_tools/cli.py`.
- Проверить runner-паттерн режимов с флагами: используется
  `_build_parser()`, а одноразовый `path_help` не вынесен в отдельную
  константу.
- Проверить dry-run контракт: `normalizer` и `syncher` пишут `.fs-log.log` при
  `--dry-run` с меткой режима `dry-run` и планом изменений.
- Проверить общий контракт логирования `.fs-log.log` для всех режимов:
  - единый формат заголовка блока (`дата`, `Инструмент`, `Режим`,
    `Результат`);
  - append-only поведение (новые прогоны дописываются, а не перезаписывают
    файл);
  - режимные маркеры пустого результата (`(изменений нет)` /
    `(нарушений нет)`) согласованы между `src/fs_tools/shared/log.py`,
    режимными `log.py`, тестами `tests/shared/test_log.py`,
    `tests/*/test_log.py` и документацией.
- Проверить контракт терминального вывода: двухстрочный финальный блок
  `Статус:` + `Сводка:` в `normalizer`/`checker`/`syncher`/`schemer` и его
  консистентность между кодом, тестами и документацией (у `schemer` статус —
  только `ok`/`error`, без `warn`).
- Проверить контракт текста веб-хуков:
  - `fs-checker - выполнен с ошибкой.`
  - `fs-syncher - выполнен с ошибкой.`
  - `fs-schemer - выполнен с ошибкой.`
  - условия отправки (checker: при missing или ошибках сканирования
    `**`-обхода (`errlist`); syncher: только production и код 2/3; schemer:
    при наличии нарушений) согласованы в раннерах, тестах и документации.
- Отсутствие необоснованных suppression-комментариев:
  - `# pylint: disable`
  - `# noqa`
  - `# type: ignore`
- Не ограничиваться только последним коммитом в режиме `audit changed`.

## Обязательные команды

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint --persistent=n --recursive=y src tests/*
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy --strict -p fs_tools
```

## Цикл выполнения

1. Найти несоответствия.
2. Исправить минимально и безопасно.
3. Повторить все 4 команды.
4. Выполнить повторный аудит тем же режимом.
5. Повторять до полного green.

## Definition of Done

- Все 4 команды зелёные.
- Нет расхождений между кодом, тестами, docs, examples, rules.
- Проверены и согласованы комментарии, а также agent/rules слой.
- Комментарии соответствуют правилам и не раздуты.
- Кроссплатформенность и безопасность соблюдены.
- Нет необоснованных suppression-комментариев.
- При необходимости обновлены `CLAUDE.md`/`.claude/rules/*.md` и/или
  `AGENTS.md` минимально и по факту.
