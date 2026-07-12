# Консистентность всегда

> Claude-эквивалент [`.cursor/rules/docs-consistency.mdc`](../../.cursor/rules/docs-consistency.mdc). Применяется всегда.

Код, тесты, примеры и документация — единое целое и не должны расходиться. Любое
изменение поведения синхронизирует все четыре пласта.

## Матрица изменений

| Тип изменения                                    | Код / тесты                                                                                   | Правила и docs                                                                                       |
|-----------------------------------------------------|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| Новое правило normalizer                            | `rules/`, `build_normalizer()`, `rules/__init__.py`/`normalizer/__init__.py` (`__all__`), `tests/normalizer/rules/test_<rule>.py`, `examples/normalizer/<NN-rule>/` | [`examples.md`](examples.md) (нумерация фикстур), README normalizer-секция                              |
| Изменение состава пакета `shared/`/`normalizer/`/`checker/`/`syncher/` | соответствующий модуль                                                                            | этот файл — раздел «Распределение по пакетам»                                                            |
| Точка входа / код возврата (`runner.main`/`run`)    | `*/runner.py`, `*/cli_args.py`                                                                    | раздел «Точки входа и коды возврата», `tests/*/test_runner.py`                                           |
| Контракт терминального вывода (`Статус:`/`Сводка:`) | `*/report.py`                                                                                     | раздел «Контракт терминального вывода», `tests/*/test_report.py`, `tests/*/test_runner.py`, `tests/*/test_examples.py`, README, `examples/*/README.md` |
| Текст/условия отправки веб-хука                     | `*/notify.py`, `runner.py`                                                                        | раздел «Контракт текста веб-хуков», `tests/checker/test_runner.py`, `tests/syncher/test_runner.py`       |
| Формат записи `.fs-log`                             | `shared/log.py`, режимные `*/log.py`                                                              | `tests/shared/test_log.py`, `tests/*/test_log.py`, [`cross-platform-safety.md`](cross-platform-safety.md) |
| Новый CLI-флаг режима                               | `*/cli_args.py`, `_build_parser()` в `runner.py`                                                  | раздел «Локальный шаблон runner-парсеров»                                                                |
| Симметрия normalizer/checker (`engine.py`, `Fs*`)   | `normalizer/engine.py`, `checker/engine.py`                                                       | раздел «Распределение по пакетам», [`naming-symmetry.md`](naming-symmetry.md)                            |
| Фильтр `.fs-ignore`                                 | `normalizer/ignore.py`                                                                            | [`path-matching.md`](path-matching.md), `tests/normalizer/test_ignore.py`                                |
| Семантика `.fs-check`                               | `checker/rule.py`, `checker/engine.py`                                                            | [`rule-matching.md`](rule-matching.md)                                                                   |
| Формат `.fs-sync.toml`                              | `syncher/config.py`                                                                               | [`config-format.md`](config-format.md)                                                                   |
| Трансляция include/exclude → rsync                  | `syncher/ignore.py`                                                                               | [`rsync-mapping.md`](rsync-mapping.md)                                                                   |
| Логика offload (`[[backup]]`)                       | `syncher/offload.py`                                                                              | [`offload-safety.md`](offload-safety.md)                                                                 |
| Новое/удалённое правило Cursor/Claude               | —                                                                                                  | [`rules-sync.md`](rules-sync.md) — карта соответствия (обе версии)                                       |

Распределение по пакетам (`src/fs_tools/`):

- `shared/` — общий код режимов: выбор каталога (`picker.py` +
 `pick_folder.ps1`), version-shim фабрики gitignore-паттернов
 (`pathspec_compat.py`, `_FACTORY`), доступ к единому `.env` (`env.py`: `load_env`
 однократно грузит `.env` в `os.environ` через `load_dotenv(override=False)` — процесс
 важнее файла; плюс путь и `chmod 600`, ленивый `dotenv`), единый журнал
 `.fs-log` (`log.py`, `append_log` — заголовок с датой/инструментом/режимом и
 `Результат:`, содержимое строк и текст пустого блока задаются параметрами), общая отправка веб-хуков (`notify.py`: URL/tok по ключам,
 https-only, lazy `requests`), общий разбор аргументов, `resolve_root` и шаблон
 `run_mode_main` (`cli.py`).
 Барьер
 «имя — один компонент пути»
  (`safety.py`) живёт в `normalizer/`, а не в `shared/`: checker ничего не
  переименовывает.
- `normalizer/` — единое объявление CLI-флагов normalizer (`cli_args.py`), правила
  (`rules/`), конвейер (`name.py`, `build_normalizer`), обход и переименование
  (`engine.py`, класс `FsNormalizer`), фильтр `.fs-ignore` (`ignore.py`), обёртка
  журнала (`log.py`, `write_fs_log`), точка входа (`runner.py`). Новое правило
  регистрируется в `build_normalizer()` и
  ре-экспортируется в `rules/__init__.py` и `normalizer/__init__.py` (`__all__`).
- `checker/` — разбор `.fs-check` (`rule.py`), разворачивание и сбор нарушений
  (`engine.py`, класс `FsChecker`), отчёт (`report.py`), веб-хук (`notify.py`,
  обёртка над `shared.notify` с ключами `FSCHK_*`),
  обёртка журнала (`log.py`), точка входа (`runner.py`).
- `syncher/` — единое объявление CLI-флагов sync (`cli_args.py`), чтение/валидация
  `.fs-sync.toml` (`config.py`, `tomllib`), трансляция include/exclude в фильтры rsync
  (`ignore.py`), сборка/запуск rsync и delete-guard (`rsync.py`), offload
  (`offload.py`), отчёт (`report.py`), веб-хук (`notify.py`, обёртка над
  `shared.notify` с ключами `FSSYN_*`), обёртка журнала (`log.py`), точка входа
  (`runner.py`).

Симметрия двух первых режимов намеренная: ядро каждого — `engine.py` с классом `Fs*`
(`FsNormalizer` / `FsChecker`); локальная переменная инстанса в `runner.run` — `fsnm`
/ `fsch`. Сохраняй это соответствие при правках. Режим `syncher` **несимметричен**: у
него нет `engine.py`/`Fs*`-класса и нет `safety.py` (структура — функциональная:
`cli_args`/`config`/`ignore`/`rsync`/`offload`/`report`, конвейер собирается в
`runner.run`).
Симметрию сохраняют только врапнеры `log.py`/`runner.py` и раскладка тестов/примеров.

Точки входа и коды возврата:

- normalizer/checker: `runner.main(argv) -> int` + `run(root, ...) -> int`. Без
  аргумента каталог выбирается интерактивно через `pick_directory()`, аргумент-каталог
  минует диалог. У normalizer есть `--dry-run` (план без переименований). Коды
  `0`/`1`/`2` зафиксированы контрактом и проверяются тестами.
- syncher: `runner.main(argv) -> int` + `run(root, args) -> int`. Без аргумента
  каталог выбирается интерактивно через `pick_directory()`, аргумент-каталог
  минует диалог. Коды `0/1/2/3` (наихудший среди профилей)
  зафиксированы контрактом.
- Диспетчер `fs_tools.cli:main` (`fs-tools <normalize|check|sync>`) и `__main__.py`
  импортируют `runner` выбранного режима **лениво** (через `importlib` в обработчике),
  чтобы
  `--help` и доступный режим работали без extra другого режима. Подкоманды
  `normalize` и `sync` объявляют флаги режима и пробрасывают их (а не только `path`).

Контракт терминального вывода:

- Финальный блок терминального вывода у `normalizer`, `checker` и `syncher`
  оформляется единообразно в две строки:
  `Статус: <ok|warn|error>. <фраза>` и
  `Сводка: <метрики в фиксированном порядке>`.
- Не возвращать в одном режиме отдельный формат наподобие `Готово...`, если
  остальные режимы уже используют `Статус:`/`Сводка:`.
- Изменения формата терминального отчёта синхронизируются между кодом
  (`*/report.py`), тестами (`tests/*/test_report.py`, `tests/*/test_runner.py`,
  `tests/*/test_examples.py`) и документацией (`README.md`, `examples/*/README.md`).

Контракт текста веб-хуков:

- Текст webhook-сообщений для режимов фиксирован и должен быть стабильным:
  - checker: `fs-checker - выполнен с ошибкой.`;
  - syncher: `fs-syncher - выполнен с ошибкой.`.
- Отправка webhook остаётся fire-and-forget и не влияет на код возврата.
- checker отправляет webhook только при наличии нарушений (`missing` не пуст).
- syncher отправляет webhook только в production-прогоне и только при
  наихудшем коде `2` или `3`.
- Любые изменения текста webhook синхронизируются между кодом раннеров,
  режимными тестами (`tests/checker/test_runner.py`,
  `tests/syncher/test_runner.py`) и документацией.

Журнал `.fs-log` — намеренное исключение из идемпотентности (дополняется на каждом
запуске), он в `.gitignore`, а `reset.*` (только у normalizer) убирают его явным
`rm`/`del`. Все режимы пишут журнал в `production` и `dry-run`; в `dry-run`
фиксируется последовательность dry-run-событий (включая конфликты/ошибки),
а откат песочницы syncher — через `git restore`/`git clean` (без `reset.*`).

Локальный шаблон runner-парсеров:

- Если в режиме есть дополнительные CLI-флаги (как `--dry-run`), парсер собирается в
  приватной функции `_build_parser()` по аналогии с `syncher/runner.py`.
- Для одноразовой подсказки `path_help` в `_build_parser()` не выноси отдельную
  константу без повторного использования.

Документация: единый `README.md` (три секции), `examples/README.md` (+ секции
режимов). Перед завершением убедись, что ни один пласт не отстал.

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
