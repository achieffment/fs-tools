# Checklist: audit-governor

## Источники истины

- `AGENTS.md`
- `README.md`
- `examples/README.md`
- `examples/checker/README.md`
- `examples/normalizer/README.md`
- `examples/syncher/README.md`
- `pyproject.toml`
- `.cursor/rules/audit-governor.mdc`
- `.cursor/rules/naming-symmetry.mdc`
- `.cursor/rules/consistency.mdc`
- `.cursor/rules/cross-platform-safety.mdc`
- `.cursor/rules/testing.mdc`
- `.cursor/rules/comments-style.mdc`
- `.cursor/rules/lazy-import-order.mdc`
- `.cursor/rules/imports.mdc`
- `.cursor/rules/examples.mdc`
- `.cursor/rules/path-matching.mdc`
- `.cursor/rules/rule-matching.mdc`
- `.cursor/rules/rsync-mapping.mdc`
- `.cursor/rules/offload-safety.mdc`
- `.cursor/rules/config-format.mdc`
- `.cursor/rules/date-rule.mdc`

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
- Проверить правила и агентные инструкции.

## Обязательные проверки качества

- Покрыть все пласты без исключений: код, тесты, examples, docs, комментарии, rules, agent guide.
- Подтвердить высокий инженерный уровень: SRP, DRY, минимализм, простота, читаемость.
- Консистентность кода, тестов, examples, docs, rules.
- Кроссплатформенность и безопасность.
- Комментарии: минимум, актуальность, выравнивание по `comments-style.mdc`.
- Проверить автоконтроль Markdown-выравнивания: `tests/shared/test_markdown_comments.py`
  проходит в составе `pytest`; для командных fenced-блоков выравнивание считается
  по локальным подблокам (между пустыми строками), опорная колонка — по самой длинной
  строке подблока.
- Проверить локальные naming-пары:
  - `src_rel/dst_rel` в `normalizer/engine.py`;
  - `map_norm_argument/add_norm_argument/norm_argv_from_namespace` в `fs_tools/cli.py`.
- Проверить runner-паттерн режимов с флагами: используется `_build_parser()`, а
  одноразовый `path_help` не вынесен в отдельную константу.
- Проверить dry-run контракт: `normalizer` и `syncher` пишут `.fs-log` при
  `--dry-run` с меткой режима `dry-run` и планом изменений.
- Проверить общий контракт логирования `.fs-log` для всех режимов:
  - единый формат заголовка блока (`дата`, `Инструмент`, `Режим`, `Результат`);
  - append-only поведение (новые прогоны дописываются, а не перезаписывают файл);
  - режимные маркеры пустого результата (`(изменений нет)` / `(нарушений нет)`)
    согласованы между `src/fs_tools/shared/log.py`, режимными `log.py`,
    тестами `tests/shared/test_log.py`, `tests/*/test_log.py` и документацией.
- Проверить контракт терминального вывода: двухстрочный финальный блок
  `Статус:` + `Сводка:` в `normalizer`/`checker`/`syncher` и его консистентность
  между кодом, тестами и документацией.
- Проверить контракт текста веб-хуков:
  - `fs-checker - выполнен с ошибкой.`
  - `fs-syncher - выполнен с ошибкой.`
  - условия отправки (checker: при missing; syncher: только production и код 2/3)
    согласованы в раннерах, тестах и документации.
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
- При необходимости обновлены `.cursor/rules/*.mdc` и/или `AGENTS.md` минимально и по факту.
