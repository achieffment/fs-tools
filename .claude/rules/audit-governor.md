# Audit-governor: обязательный контракт аудита

> Claude-эквивалент [`.cursor/rules/audit-governor.mdc`](../../.cursor/rules/audit-governor.mdc). Применяется всегда.

Для запросов аудита использовать единый подход — режим `audit changed`
(аудит внесённых правок) или `audit full` (полный аудит проекта). Полный
контракт (охват, критерии качества, spot-checks, обязательный цикл команд,
stop-condition) — в skill [`audit-governor`](../skills/audit-governor/SKILL.md),
не дублируется здесь.

`pylint` ожидаемо сообщает `R0801` (duplicate-code) между
`tests/checker/test_runner.py`, `tests/schemer/test_runner.py` и
`tests/syncher/test_offload.py` — это следствие намеренной параллельной
раскладки тестов режимов (см. [`testing.md`](testing.md),
[`naming-symmetry.md`](naming-symmetry.md)), не повод к рефакторингу «до
green» по этому конкретному предупреждению.
