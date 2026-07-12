# Именование и симметрия переменных

> Claude-эквивалент [`.cursor/rules/naming-symmetry.mdc`](../../.cursor/rules/naming-symmetry.mdc). Применяется всегда.

Применяй единый словарь и симметрию длин для логически связанных локальных имён.
Цель — визуальная ровность соседних переменных без потери смысла.

## Карта сокращений режимов

Каждый режим имеет один и тот же 3-буквенный код во всех слоях, где он вообще
нужен, — файле-артефакте, env-префиксе веб-хука и 4-буквенном коде в исходниках.
Не вводи для одного режима третий вариант сокращения без внесения его в эту
таблицу.

| Режим      | Код | Файл-артефакт  | Env-префикс (`shared/notify.py`) | Код (инстанс/переменная)                                                                                     |
|------------|-----|----------------|----------------------------------|--------------------------------------------------------------------------------------------------------------|
| normalizer | nrm | `.fs-nrm`      | — (без веб-хука)                 | `fsnm`                                                                                                       |
| checker    | chk | `.fs-chk`      | `FSCHK`                          | `fsch`                                                                                                       |
| syncher    | syn | `.fs-syn.toml` | `FSSYN`                          | `fssy` (только `cli.py`; `syncher` не заводит `Fs*`-класс, см. [`docs-consistency.md`](docs-consistency.md)) |
| schemer    | sch | `.fs-sch.toml` | `FSSCH`                          | `fssm`                                                                                                       |

- Все четыре файла-артефакта — скрытые (ведущая точка): нормализатор и checker
  читают их из корня проверяемого каталога, syncher и schemer — аналогично
  (см. [`scheme-format.md`](scheme-format.md)).
- Код в 4-буквенном виде — `fs` + 2 буквы кода режима; для schemer сокращение
  `sm` (а не `sc`) закреплено исторически, менять не нужно.

## Базовый словарь замен

- `local -> source`
- `remote -> target`
- `archive -> backup`
- `archive_dir -> backup_dir` (внешний TOML -> внутренние поля/параметры)
- `raw -> bare`
- `dir -> path` (по смыслу; искусственное `dirr` не вводим)
- `local_root -> source_root` (внешний TOML -> внутренняя модель синхронизации)
- `remote_root -> target_root` (внешний TOML -> внутренняя модель синхронизации)
- `stamp -> date`
- `content -> cont`
- `token -> tok`
- `separator -> sep`
- `slash -> slh`
- `profiles -> roll`
- `process -> proc`
- `title -> header`
- `convert -> conv`
- `returncode -> rc` (кроме stdlib-контрактов)
- `current -> curr`
- `reports -> result`
- `operations -> actions`
- `confirmed -> confirm`
- `offloaded -> offload`
- `errors -> errlist`
- `drive -> disk`

## Допустимые сокращения из истории проекта

- `target -> targ` (например `resolve_root(targ)`)
- пары `source/target -> src/dst` в плотных локальных блоках
- `source_path/target_path -> srcp/dstp` при длинных цепочках путей
- `index/left/right/middle/right_tail -> ix/lf/rt/md/rtail`
- `anchor_count -> anccnt`
- `include -> incl`
- `regex -> rx`
- `log_path -> lpath`
- `shared/managed/converted -> shar/mang/con|conv`
- инстансы режимов: `fsnm` (normalizer), `fsch` (checker), `fssm` (schemer)
- те же имена инстансов (`fsnm`/`fsch`/`fssm`) применяются и в тестах, не только в `runner.py`

### Локальные пары для CLI-диспетчера (fs_tools/cli.py)

- Это частный случай общего правила локальной симметрии для соседних переменных.
- Для normalizer-блока использовать компактную тройку:
  `map_norm_argument` / `add_norm_argument` / `norm_argv_from_namespace`.
- Для sync-блока сохранять существующую тройку:
  `map_sych_argument` / `add_sync_argument` / `sync_argv_from_namespace`.
- Не смешивать в одном блоке формы `normalizer_*` и `norm_*` без причины.

### Локальные пары путей в normalizer/engine.py

- Для относительных путей в одном блоке использовать симметричную пару
  `src_rel` / `dst_rel` (не `src_rel` / `dest_rel`).

## Правило подбора имени

- Выравнивай только логических «соседей» в одном блоке/функции.
- Не выравнивай «вообще всё»; локальная симметрия важнее глобального переименования.
- Если в одном блоке появляются однотипные переменные с нумерацией (`name1`, `name2`),
  нумерация обязательна для всей пары/серии: не смешивай `name` и `name2`;
  используй `name1`, `name2` (и далее `name3` при необходимости).
- Предпочтение:
  1. полная читабельная форма (`source/target`, `confirm/offload/errlist`);
  2. краткая симметричная форма (`src/dst`, `sep/slh`, `url/tok`), если модуль уже в таком стиле.
- В пределах одного модуля не смешивай хаотично полные и краткие формы одной сущности.

## Исключения (не переименовывать)

- Контракты stdlib и внешних API (`proc.returncode`, `CompletedProcess.returncode`).
- Публичные контракты, требующие отдельной миграции (внешние CLI/env/TOML поля), если задача явно не про миграцию.
- Устойчивые имена протоколов/колбэков (`os.walk`: `dirpath/dirnames/filenames`,
  `Path.is_dir`) — сохраняются, если переименование ухудшает читаемость.
- Текстовые данные фикстур/примеров, где слова являются содержимым, а не именами переменных.

## Примеры

- Хорошо: `source_path`, `target_path`; `sep`, `slh`; `result`, `actions`.
- Хорошо: `confirm`, `offload`, `errlist` (тройка одинаковой длины).
- Плохо: смешивать `target` и `targ` в одном небольшом блоке без причины.
