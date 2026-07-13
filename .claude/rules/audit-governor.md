# Audit-governor: обязательный контракт аудита

> Claude-эквивалент [`.cursor/rules/audit-governor.mdc`](../../.cursor/rules/audit-governor.mdc). Применяется всегда.

Практический запуск в Claude Code — skill [`audit-governor`](../skills/audit-governor/SKILL.md).

Для запросов аудита использовать единый подход:

- режим `audit changed` — аудит всех внесенных правок;
- режим `audit full` — аудит всего проекта.

## Обязательный охват

Проверяются все пласты без исключений:

- код;
- тесты;
- примеры;
- документация;
- комментарии;
- правила проекта (`.claude/rules/*.md` / `.cursor/rules/*.mdc`);
- агентные инструкции (`AGENTS.md`).

## Критерии качества

- высокий инженерный уровень реализации;
- SRP, DRY, минимализм, простота, читаемость;
- консистентность между всеми пластами;
- кроссплатформенность и безопасность;
- отсутствие необоснованных suppression-комментариев.

## Обязательные точечные проверки (spot-checks)

- dry-run контракт: `normalizer` и `syncher` при `--dry-run` пишут `.fs-log.log`
  с пометкой `Режим: dry-run` и последовательностью dry-run-событий;
- runner-паттерн: режимы с собственными флагами используют `_build_parser()`;
- одноразовый `path_help` не выносится в отдельную константу без повторного
  использования;
- локальная симметрия имён в критичных блоках:
  - `src_rel`/`dst_rel` в `normalizer/engine.py`;
  - `map_norm_argument`/`add_norm_argument`/`norm_argv_from_namespace` в
    `fs_tools/cli.py`.

## Обязательный цикл

После исправлений запускать до полного green:

    .venv/bin/python -m pytest -q
    .venv/bin/python -m pylint --persistent=n --recursive=y src tests/*
    .venv/bin/python -m ruff check .
    .venv/bin/python -m mypy --strict -p fs_tools

При расхождении IDE-диагностики и общего `pylint` обязателен точечный запуск:

    .venv/bin/python -m pylint --persistent=n tests/path/to/file.py

`pylint` ожидаемо сообщает `R0801` (duplicate-code) между
`tests/checker/test_runner.py`, `tests/schemer/test_runner.py` и
`tests/syncher/test_offload.py` — это следствие намеренной параллельной
раскладки тестов режимов (см. [`testing.md`](testing.md),
[`naming-symmetry.md`](naming-symmetry.md)), не повод к рефакторингу «до
green» по этому конкретному предупреждению.

## Stop-condition аудита

Аудит считается **закрытым**, когда выполнены все пункты ниже. Дальнейшие правки —
только по новой задаче, не «дочистка аудита»:

1. **`git status`** — чистая working tree (или весь WIP в одном атомарном коммите);
2. **Единый gate один раз в конце** (не по слоям, см. «Обязательный цикл» выше);
3. Все gate зелёные и нет открытых расхождений docs ↔ код ↔ тесты ↔ examples;
4. **Не коммитить** слайсовые «закрытие аудита» без связки: код + тесты + examples +
   docs (см. [`docs-consistency.md`](docs-consistency.md)).

## Гибкость правил

Если для прохождения проверок требуется корректировка `.claude/rules/*.md` /
`.cursor/rules/*.mdc` или `AGENTS.md`, изменения вносятся минимально, согласованно
и только по фактической необходимости.
