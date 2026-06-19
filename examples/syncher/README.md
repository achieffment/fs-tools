# examples/syncher — песочница синхронизации

Запускаемое дерево для прогона `fs-syncher` **без сети**. Оба профиля используют
локальные каталоги-приёмники (`remote_root` указывает на каталоги внутри песочницы),
поэтому результат детерминирован и воспроизводим, а `--dry-run` не имеет побочных
эффектов. Правила подобраны так, чтобы показать работу на уровне **каталогов**
(исключение и возврат папок целиком).

## Состав

    examples/syncher/
    ├── .fs-sync.toml              профили [[sync]] «site» и [[backup]] «vault»
    ├── source/                    источник профиля «site»
    │   ├── projects/alpha/        идентичен server/ → не передаётся (checksum)
    │   │   ├── main.py
    │   │   ├── README.md
    │   │   └── node_modules/      исключён правилом node_modules/
    │   ├── projects/beta/         нет на сервере → каталог передаётся (+)
    │   ├── projects/keep/build/   возвращён include = ["projects/keep/build/"] → передаётся
    │   ├── cache/                 исключён правилом cache/
    │   ├── build/                 исключён правилом build/ (верхнего уровня)
    │   └── docs/                  нет на сервере → передаётся (+)
    ├── server/                    «сервер» профиля «site» (локальный приёмник)
    │   ├── projects/alpha/        совпадает с источником
    │   └── obsolete-project/      нет в источнике → удаляется зеркалированием (-)
    ├── archive/                   источник профиля «vault» (offload)
    │   ├── 2026-01/
    │   └── 2026-02/
    └── server-archive/            «сервер» профиля «vault» (пустой приёмник)

## Как запустить

```bash
# из корня проекта; канонический прогон — dry-run (без изменений)
bin/sync.sh examples/syncher --dry-run          # Linux/macOS (терминал)
bin/sync.command examples/syncher --dry-run     # macOS (двойной клик в Finder)
bin/sync.bat examples/syncher --dry-run         # Windows (через WSL/cwrsync)
```

Эквивалент напрямую: `fs-syncher examples/syncher --dry-run` (или
`fs-tools sync examples/syncher --dry-run`).

### Запуск из WSL с Windows-диска

Если проект расположен на Windows-диске, запускайте Linux-обёртку и передавайте корень
песочницы в формате `/mnt/<disk>/...`:

```bash
/home/<user>/Home/Components/fs-tools/bin/sync.sh /mnt/e/Home/Components/fs-tools/examples/syncher --dry-run
```

Такой запуск использует единый Linux-стек `rsync`/`ssh` и избегает смешивания
Windows OpenSSH и chocolatey/cwrsync runtime.

## Что демонстрирует `.fs-sync.toml`

- **`[defaults]`** — общие пороги delete-guard для всех профилей;
- **`[[sync]]` «site»** — зеркалирование с `delete = true` (удаления, в т.ч. целых
  папок, переносятся на сервер), `checksum = true` (совпадающие по содержимому файлы
  не передаются), исключение **каталогов** (`node_modules/`, `cache/`, `build/`) и
  возврат одного каталога `include = ["projects/keep/build/"]` поверх правила
  `build/` — это и есть override на уровне папок;
- **`[[backup]]` «vault»** — offload с `after_push = "archive"` и `verify = true`.

## Ожидаемый итог `--dry-run`

```text
Профиль «site» (sync): передано 3, удалено 2, выгружено 0, ошибок 0
Профиль «vault» (backup): передано 3, удалено 0, выгружено 0, ошибок 0
```

Как читать результат профиля «site»:

| Каталог/объект | Итог | Почему |
|----------------|------|--------|
| `projects/beta/` | передан (`+`) | нового проекта нет на сервере (1 файл) |
| `docs/` | передан (`+`) | новой папки нет на сервере (1 файл) |
| `projects/keep/build/` | передан (`+`) | исключён правилом `build/`, но возвращён `include` (1 файл) |
| `projects/alpha/` | пропущен | содержимое совпадает с сервером (сверка `checksum`) |
| `projects/alpha/node_modules/` | пропущен | каталог исключён `node_modules/` |
| `cache/`, `build/` | пропущены | каталоги исключены целиком |
| `server/obsolete-project/` | удалён (`-`) | нет в источнике; удаляется и файл, и сама папка (отсюда «удалено 2») |

«Передано 3» — это `projects/beta/main.py`, `docs/guide.md` и
`projects/keep/build/keep.bin` (создаваемые каталоги в счётчик не идут — они
структурные). «Удалено 2» — `obsolete-project/old.txt` и сам каталог
`obsolete-project/`.

Профиль «vault» в `--dry-run` показывает план передачи трёх файлов архива из папок
`2026-01/` и `2026-02/`; локальные файлы не трогаются, перенос в `_fs-backup`
выполняется только в боевом режиме после подтверждённой передачи.

## Боевой прогон и сброс

Боевой прогон (без `--dry-run`) **изменяет** песочницу: наполняет `server/`,
зеркалит удаление каталога `obsolete-project/`, а offload переносит файлы из
`archive/` в `_fs-backup/`. Восстановить исходное состояние можно из git:

```bash
git restore examples/syncher
git clean -fd examples/syncher    # уберёт _fs-backup/, .fs-log и прочие следы прогона
```

> Пустые каталоги git не хранит, поэтому в `server-archive/` лежит файл-заглушка
> `.gitkeep`. На синхронизацию он не влияет (это каталог-приёмник).
