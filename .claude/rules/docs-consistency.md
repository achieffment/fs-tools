# Консистентность всегда

> Claude-эквивалент [`.cursor/rules/docs-consistency.mdc`](../../.cursor/rules/docs-consistency.mdc). Применяется всегда.

Код, тесты, примеры и документация — единое целое и не должны расходиться. Любое
изменение поведения синхронизирует все четыре пласта.

## Роли артефактов

| Слой                            | Файлы                                                          | Содержит                                                           |
|---------------------------------|----------------------------------------------------------------|--------------------------------------------------------------------|
| **Поведение (источник истины)** | `src/fs_tools/`                                                | Реализация режимов, контракты (коды возврата, отчёт, веб-хук)      |
| **Канон проекта (AI)**          | `.claude/rules/*.md` / `.cursor/rules/*.mdc`                   | Детальные политики по областям (см. таблицу в `AGENTS.md`)         |
| **Справочник AI**               | [`AGENTS.md`](../../AGENTS.md), [`CLAUDE.md`](../../CLAUDE.md) | Раскладка, workflow, сводная таблица правил, ссылки на все правила |
| **Документация людей**          | [`README.md`](../../README.md)                                 | Onboarding, установка, режимы CLI — кратко, без полных политик     |

Не копировать детальные политики из `.claude/rules/*.md` в README/`AGENTS.md`
(см. «Антипаттерны» ниже) — там только ссылка.

Детальная матрица «тип изменения → что править в коде/тестах/docs» и
распределение исходников по пакетам `src/fs_tools/` — в
[`docs-consistency-matrix.md`](docs-consistency-matrix.md) (загружается только
при работе с `src/fs_tools/**`/`tests/**`/`examples/**`, не дублируется здесь).

## Порядок работы

1. Код, тесты, примеры — по затронутому режиму;
2. Полный цикл: `pytest`, `pylint --persistent=n --recursive=y src tests/*`, `ruff check .`,
   `mypy --strict -p fs_tools`;
3. Правила по «Матрице изменений» ([`docs-consistency-matrix.md`](docs-consistency-matrix.md)) —
   в обоих каталогах (`.claude/rules/*.md` и `.cursor/rules/*.mdc`);
4. [`AGENTS.md`](../../AGENTS.md) → [`CLAUDE.md`](../../CLAUDE.md) → `README.md`;
5. Финальный чеклист (ниже).

## Антипаттерны

- Изменить поведение и не прогнать полный цикл проверок из
  [`audit-governor.md`](audit-governor.md) перед фиксацией «готово».
- Развести расхождение между кодом и парой `.claude/rules/*.md` /
  `.cursor/rules/*.mdc` — см. [`rules-sync.md`](rules-sync.md).
- Дублировать детальные политики режимных правил (`path-matching.md`,
  `rule-matching.md`, `config-format.md` и т.д.) в README или `AGENTS.md`
  вместо ссылки на них.
- Обновить только один пласт (например, код) из «Матрицы изменений», оставив
  тесты/примеры/документацию отставшими.

## Финальный чеклист

- [ ] Имена/состав пакетов согласованы в коде, тестах, examples и docs;
- [ ] Политики актуальны в затронутых `.claude/rules/*.md` и парном `.mdc`;
- [ ] `AGENTS.md`/`CLAUDE.md`/`README.md` соответствуют канону (правила
      таблицы/списка не отстали от карты в [`rules-sync.md`](rules-sync.md));
- [ ] `pytest`, `pylint --persistent=n --recursive=y src tests/*`, `ruff check .`,
      `mypy --strict -p fs_tools` — зелёные;
- [ ] Выравнивание markdown-таблиц/inline-комментариев актуально
      (`tests/shared/test_markdown_tables.py`,
      `tests/shared/test_markdown_comments.py`).
