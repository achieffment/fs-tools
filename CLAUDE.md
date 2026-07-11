# CLAUDE.md

Справочник и правила проекта для Claude Code — эквивалент `.cursor/rules/`
для Cursor. Основной AI-справочник — @AGENTS.md.

## Правила (Claude)

Детальные политики — в `.claude/rules/` (перенесены из `.cursor/rules/*.mdc`,
содержание синхронизировано):

- [`.claude/rules/audit-governor.md`](.claude/rules/audit-governor.md) — единый контракт аудита правок и всего проекта; практический запуск — skill [`audit-governor`](.claude/skills/audit-governor/SKILL.md);
- [`.claude/rules/consistency.md`](.claude/rules/consistency.md) — консистентность кода, тестов, examples и документации; точки входа и коды возврата;
- [`.claude/rules/cross-platform-safety.md`](.claude/rules/cross-platform-safety.md) — кроссплатформенность и безопасность файловых операций (Windows/WSL/macOS/Linux);
- [`.claude/rules/naming-symmetry.md`](.claude/rules/naming-symmetry.md) — словарь замен и симметрия локальных имён переменных;
- [`.claude/rules/testing.md`](.claude/rules/testing.md) — тесты режимов, обязательные проверки, демо-инварианты;
- [`.claude/rules/comments-style.md`](.claude/rules/comments-style.md) — стиль комментариев в коде и выравнивание inline-комментариев в документации;
- [`.claude/rules/imports.md`](.claude/rules/imports.md) — порядок импортов (PEP 8 / isort);
- [`.claude/rules/lazy-import-order.md`](.claude/rules/lazy-import-order.md) — порядок последовательных блоков `importlib.import_module`;
- [`.claude/rules/config-format.md`](.claude/rules/config-format.md) — формат и валидация `.fs-sync.toml` (`syncher`);
- [`.claude/rules/offload-safety.md`](.claude/rules/offload-safety.md) — безопасность offload, профиль `[[backup]]` (`syncher`);
- [`.claude/rules/rsync-mapping.md`](.claude/rules/rsync-mapping.md) — трансляция include/exclude в фильтры rsync (`syncher`);
- [`.claude/rules/date-rule.md`](.claude/rules/date-rule.md) — осознанные допущения `DateRule` (`normalizer`);
- [`.claude/rules/path-matching.md`](.claude/rules/path-matching.md) — фильтр `.fs-ignore`, gitignore-семантика (`normalizer`);
- [`.claude/rules/rule-matching.md`](.claude/rules/rule-matching.md) — семантика `.fs-check`, разворачивание и негативы (`checker`);
- [`.claude/rules/examples.md`](.claude/rules/examples.md) — формирование примеров-фикстур по режимам;
- [`.claude/rules/rules-sync.md`](.claude/rules/rules-sync.md) — двусторонняя синхронизация правил Cursor (`.mdc`) и Claude (`.md`).

Перед правками в соответствующей области — прочитать релевантное правило.

## Синхронизация с Cursor

Проект поддерживает оба редактора: `.cursor/rules/*.mdc` (Cursor) и
`.claude/rules/*.md` (Claude Code) содержат один и тот же канон. При
изменении политики — обновлять обе версии одновременно (см.
[`.claude/rules/rules-sync.md`](.claude/rules/rules-sync.md)).
