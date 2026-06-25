# fs-tools

Набор кросс-платформенных CLI-утилит для работы с файловой системой, собранный в один
устанавливаемый пакет с общим ядром:

- **нормализация имён** (`fs-normalizer`) — рекурсивно приводит имена файлов и папок к единому
  виду: транслитерация в ASCII, даты в ISO, единый стиль разделителей и регистра.
  Идемпотентна: повторный прогон над уже нормализованным деревом ничего не меняет
  (кроме служебного журнала);
- **проверка структуры** (`fs-checker`) — рекурсивно сверяет дерево с правилами `.fs-check`
  (синтаксис как у `.gitignore`, но смысл инвертирован: перечисленное **обязано
  существовать**) и печатает список отсутствующих путей. Структуру **не меняет**;
- **синхронизация** (`fs-syncher`) — односторонняя синхронизация каталога с сервером
  (ПК → сервер) через внешний `rsync` по декларативному `.fs-sync.toml`. Состав
  передачи, зеркалирование удалений (с защитой delete-guard) и выгрузка-offload
  задаются профилями.

Все режимы доступны и по отдельности, и через единый диспетчер `fs-tools`.

## Требования

- Python 3.11+.
- Базовая зависимость: [pathspec](https://pypi.org/project/pathspec/) (gitignore-семантика
  для `.fs-ignore` и негативов `.fs-check`).
- Опциональные зависимости по режимам (extras):
  - `normalizer` → [Unidecode](https://pypi.org/project/Unidecode/) (транслитерация);
  - `checker` → [requests](https://pypi.org/project/requests/),
    [python-dotenv](https://pypi.org/project/python-dotenv/) (веб-хук и `.env`);
  - `syncher` → [requests](https://pypi.org/project/requests/),
    [python-dotenv](https://pypi.org/project/python-dotenv/) (веб-хук и `.env`).
- Внешние бинарники для синхронизации: `rsync` (обязателен), `ssh` (для SSH-целей).

Тяжёлые зависимости подгружаются **лениво**: можно поставить только нужный extra, и
другие режимы не будут требовать чужих пакетов. Для выбора каталога GUI-пакеты не нужны:
Windows/WSL — нативный `IFileOpenDialog` через `powershell.exe`, macOS — `osascript`,
обычный Linux — ввод пути в терминале.

## Установка

Проект рассчитан на локальную editable-установку (не на публикацию в PyPI):

```bash
python3 -m venv .venv
source .venv/bin/activate                             # Windows: .venv\Scripts\activate
pip install -e ".[normalizer,checker,syncher]"        # все режимы
# или частично:
pip install -e ".[normalizer]"                        # только нормализатор
pip install -e ".[checker]"                           # только проверка
pip install -e ".[syncher]"                           # только синхронизация
pip install -e ".[normalizer,checker,syncher,dev]"    # + инструменты разработки
```

После установки доступны команды `fs-normalizer`, `fs-checker`, `fs-syncher`,
`fs-tools` (и `python -m fs_tools`).

### Windows (Chocolatey + rsync)

Для запуска `fs-syncher` напрямую из Windows установите `rsync` через Chocolatey:

1. Установите Chocolatey по официальной инструкции:
   [https://chocolatey.org/install#individual](https://chocolatey.org/install#individual)
2. Откройте терминал **от имени администратора** и установите rsync:

```powershell
choco install rsync -y
```

3. Проверьте доступность бинаря:

```powershell
rsync --version
```

Если `rsync` не найден в IDE-терминале после установки, полностью перезапустите IDE
и создайте новый терминал (чтобы обновился `PATH`).

### Обёртки `bin/`

Для запуска без ручной подготовки окружения есть обёртки в [`bin/`](bin/): при первом
запуске они создают `.venv` в корне проекта, ставят пакет со всеми extra и экспортируют
`FS_TOOLS_HOME` (нужно для поиска единого `.env`).

```bash
bin/normalize.sh [каталог]        # Linux/macOS (терминал) → fs-normalizer
bin/check.sh [каталог]            # Linux/macOS (терминал) → fs-checker
bin/sync.sh [каталог] [флаги]     # Linux/macOS (терминал) → fs-syncher
bin/normalize.command             # macOS (двойной клик в Finder)
bin/check.command                 # macOS (двойной клик в Finder)
bin/sync.command                  # macOS (двойной клик в Finder)
bin/normalize.bat [каталог]       # Windows → fs-normalizer
bin/check.bat [каталог]           # Windows → fs-checker
bin/sync.bat [каталог] [флаги]    # Windows (через WSL/cwrsync) → fs-syncher
```

## Использование

Без аргумента каталог выбирается интерактивно (по умолчанию предлагается рабочий
каталог). Каталог можно передать **аргументом** — тогда диалог не открывается:

```bash
fs-normalizer                           # нормализация: выбрать каталог в диалоге
fs-normalizer /path/to/dir              # без диалога
fs-normalizer /path/to/dir --dry-run

fs-checker                 # проверка: выбрать каталог в диалоге
fs-checker /path/to/dir    # без диалога

fs-syncher                 # синхронизация: выбрать каталог в диалоге
fs-syncher /path/to/dir    # без диалога

fs-tools normalize /path/to/dir              # то же через диспетчер
fs-tools normalize /path/to/dir --dry-run
fs-tools check /path/to/dir
fs-tools sync /path/to/dir

python -m fs_tools normalize                 # эквивалент fs-tools normalize
```

Запуск по таймеру — с фиксированным путём в команде, поэтому стартовый рабочий каталог
не важен:

```bash
# crontab -e
0 3 * * * /path/to/fs-tools/bin/normalize.sh /mnt/disk/Home    # нормализация ночью
0 9 * * * /path/to/fs-tools/bin/check.sh /mnt/disk/Home        # проверка утром
0 1 * * * /path/to/fs-tools/bin/sync.sh /mnt/disk/Home         # синхронизация ночью
```

---

## Режим нормализации (`fs-normalizer`)

### Правила

Применяются к имени (для файлов — без расширения) строго по порядку:

| # | Правило | Что делает |
|---|---------|------------|
| 1 | `TransliterationRule` | Не-ASCII → ASCII (`ь`/`ъ` удаляются, апострофа не дают); разделители пути и управляющие символы из транслитерации (`½`→`1/2`, `∖`→`\`) → `-`; запрещённые на Windows `< > : " \| ? *` (из `«»`→`<<`/`>>`) вырезаются |
| 2 | `BracketsRule` | Скобки с числом/датой → убираются (`(1)`/`[1]`→`1`); с текстом → сохраняются; непарные/несовпадающие → вырезаются |
| 3 | `DateRule` | Даты → ISO `YYYY-MM-DD`; недостающие части → `00` |
| 4 | `SpaceToDashRule` | Пробелы → дефис; цепочки вокруг пробела схлопываются, намеренные `file--improved` сохраняются |
| 5 | `TrimEdgeRule` | Обрезка «мусора» по краям (ведущий `_` сохраняется; парная скобка на краю сохраняется; `+`/`#` — символы имени: `C#`, `C++`, `notepad++`) |
| 6 | `LeadingZeroRule` | Одиночный числовой токен → с ведущим нулём (`1_file`→`01_file`) |
| 7 | `CaseRule` | Папки — с заглавной, файлы — в нижнем регистре (`README` сохраняется); у папок ведущий `_` сохраняется (`_private`→`_Private`) |

Порядок важен: `LeadingZeroRule` после `TrimEdgeRule`, `CaseRule` — последним; это
обеспечивает корректность и идемпотентность за один проход. Расширение файла не
меняется. Скрытые объекты (на `.`) и корневой каталог не трогаются.

Примеры: `Отчёт.TXT`→`otchiot.TXT`, `Файл (1).docx`→`fail-01.docx`,
`20.05.2020_dump`→`2020-05-20_dump`, `отчёт за март`→`Otchiot-za-mart` (папка).

### Фильтр путей `.fs-ignore`

Положите файл `.fs-ignore` **в нормализуемый каталог** (как `.gitignore` в корне репозитория).
Полный синтаксис gitignore поверх `pathspec`: `*`, `**`, `?`, `[abc]`, завершающий `/`,
якоря (`/foo` — от корня, `foo` — basename на любой глубине), `!` — возврат (override),
порядок строк значим. Матчинг регистронезависим. Нет файла → фильтр выключен. Без правил-`!`
внутрь исключённых каталогов обход не заходит; исключённые объекты в счётчики не попадают.

### Коды возврата

| Код | Условие |
|-----|---------|
| 0 | прогон без реальных ошибок (безопасно пропущенные конфликты входят сюда) |
| 1 | ошибка запуска: каталог не выбран / не найден / не каталог, либо не установлен extra `normalizer` (`Unidecode`) |
| 2 | часть переименований не удалась (`OSError`: напр. зарезервированные имена Windows, длина пути) |

Конфликт (занятое целевое имя) — безопасный пропуск, на код возврата не влияет.

### Dry-run (`--dry-run`)

`--dry-run` строит план нормализации без переименования объектов. В отчёте режим
помечается как `dry-run`. В этом режиме `.fs-log` содержит планируемые изменения.

### Публичное API

```python
from pathlib import Path

from fs_tools.normalizer import build_normalizer, FsNormalizer, load_fs_ignore, write_fs_log

build_normalizer().normalize("Отчёт 2020", is_dir=True)    # 'Otchiot_2020-00-00'

target = Path("/path/to/dir")
fsnm = FsNormalizer(build_normalizer(), load_fs_ignore(target))
renamed, skipped = fsnm.apply(target)
write_fs_log(target, fsnm.renames)                         # дописать .fs-log

renamed, skipped = fsnm.apply(target, dry_run=True)        # только план, без rename
fsnm.planned                                               # пары src -> dst для dry-run
```

---

## Режим проверки (`fs-checker`)

### Формат `.fs-check`

Файл лежит **в корне проверки** и читается оттуда. Синтаксис близок к `.gitignore`, но
перечисленное **обязано существовать**.

- Кодировка `utf-8-sig`; разделитель сегментов — POSIX `/`. Комментарий — только ведущий
  `#`; пустые строки игнорируются; конечные пробелы обрезаются (значимый — `\ `).
- Сегменты: литерал, `*` (один уровень), `**` (ноль и более), глоб внутри сегмента.
- Мандат — последний сегмент. Завершающий `/` → строго каталог (`is_dir()`); без него —
  `exists()` (файл или папка).
- Негативы `!` работают через единый ordered pathspec-канал: матч по относительным
  путям якоря и мандата (`anchor/require`), поддержка масок `**`, `*`, `?`, `[]`,
  порядок строк значим (`last-match-wins`).
- В checker `!` — только исключение из проверки: re-include не используется.
  Ведущие `!` схлопываются, поэтому `!!/Code/PHP/**` трактуется как `!/Code/PHP/**`.

```gitignore
# фиксированные каталоги — отдельными правилами-литералами
/Activities
/Activities/Web/Projects
# подстановка: в каждом занятии
/Activities/*/Projects
# строго каталог (завершающий /)
/Activities/Web/Projects/Addl/
# обязательный файл (мандат-файл)
/Activities/Web/Projects/Work/*/*/Data/project.md
# архивные проекты на любом уровне
/Activities/Web/Projects/**/_Archive/*/Back
# short pathspec-паттерн: исключить ветки _Archive на любой глубине
!_Archive
```

Фиксированные промежуточные каталоги описывают отдельными правилами-литералами: иначе их
отсутствие маскирует более глубокие нарушения (нет якоря — нечего проверять).

### Вывод и коды возврата

```text
Каталог: /mnt/disk/Home
Отсутствуют пути (4):
  Activities/3D/Resources
  Activities/Web/Projects/Addl/safegrid.example/Data
  Activities/Web/Projects/Self/personal.example/Back
  Activities/Web/Projects/Work/Fabrikam/widgets.example/Data/project.md
Проверено правил: 17. Найдено каталогов-кандидатов: 22. Отсутствует: 4.
```

| Код | Условие |
|-----|---------|
| 0 | нарушений нет |
| 1 | ошибка запуска: каталог не выбран / не найден / не каталог, нет `.fs-check` |
| 2 | проверка выполнена, найдены отсутствующие пути |

### Уведомления (веб-хук) и `.env`

Проверка всегда дописывает журнал `.fs-log`; при нарушениях дополнительно шлёт
fire-and-forget веб-хук
(`POST {"text": ...}` с заголовком `Authorization: Bearer <токен>`, если токен задан;
сетевые ошибки гасятся и на код возврата не влияют).

Конфигурация — в едином `.env` проекта. Путь: `FS_TOOLS_HOME/.env` (переменную
экспортируют обёртки `bin/*`), при отсутствии переменной — `.env` в текущем рабочем
каталоге. Шаблон — [`.env.example`](.env.example):

```dotenv
FSCHK_WEBHOOK_URL=https://example.com/hook
FSCHK_WEBHOOK_TOK=секретный-токен
```

Особенности конфигурации веб-хука:

- **приоритет**: переменные окружения процесса важнее значений из `.env`;
- **только HTTPS**: не-`https://` URL отвергается (токен не уходит по нешифрованному каналу).

Без `FSCHK_WEBHOOK_URL` уведомления отключены; токен необязателен.

### Публичное API

```python
from pathlib import Path

from fs_tools.checker import FsChecker, format_report, load_fs_rule

root = Path("/path/to/dir")
fsch = FsChecker(load_fs_rule(root)).check(root)
print(format_report(root, fsch))              # fsch.missing — отсортированный список
```

---

## Режим синхронизации (`fs-syncher`)

Односторонняя синхронизация локального каталога с сервером (**ПК → сервер**) через
внешний `rsync` поверх SSH (или в локальный каталог). Утилита — тонкая обёртка над
`rsync`: читает и валидирует `.fs-sync.toml`, транслирует правила include/exclude в
фильтры `rsync` (сопоставление путей выполняет сам `rsync`), запускает команду,
разбирает итог, дописывает `.fs-log` и при необходимости шлёт веб-хук.

Без аргумента каталог выбирается интерактивно (диалог проводника на Windows и в WSL,
диалог macOS, либо ввод пути в терминале на Linux). Каталог можно передать аргументом
— тогда диалог не открывается.

```bash
fs-syncher                                # выбрать каталог и запустить все профили
fs-syncher /path/to/dir                   # все профили из .fs-sync.toml
fs-syncher /path/to/dir --dry-run         # план без передачи/удаления
fs-syncher /path/to/dir --profile site    # только профиль «site» (флаг повторяемый)
fs-tools sync /path/to/dir                # то же через диспетчер
```

Флаги: `--profile NAME` (повторяемый), `--all` (все профили — поведение по умолчанию),
`--dry-run` (приоритетнее `dry_run` профиля), `--force-delete` (снять delete-guard).

> **Windows:** нативного `rsync` нет — запускайте режим через **WSL** (рекомендуется)
> или **cwrsync**. Пути для `rsync` приводятся к posix.

#### Простой Windows-сценарий (cwrsync, без WSL)

Конфиг держим в корне `E:\Home` и задаём относительный источник только для нужной
папки:

```toml
[[sync]]
name = "access"
local_root = "Access"
remote_root = "user@host:/mnt/disk/Home/Access"
delete = false
checksum = true
```

Запуск:

```bat
bin\sync.bat "E:\Home" --dry-run --profile access
```

Такой профиль синхронизирует только `E:\Home\Access` и не требует UNC-путей вроде
`\\localhost\...`.

#### Сценарий через WSL (рекомендуется)

Если данные лежат на Windows-диске, запускайте `sync.sh` из WSL, а каталог передавайте
в формате `/mnt/<disk>/...`:

```bash
sudo apt update
sudo apt install -y rsync openssh-client
/home/<user>/Home/Components/fs-tools/bin/sync.sh /mnt/e/Home --dry-run --profile access
```

Здесь `/mnt/e/Home` соответствует `E:\Home`, а `local_root = "Access"` в
`.fs-sync.toml` остаётся относительным и безопасно ограничивает область синхронизации.

#### Troubleshooting: `The source and destination cannot both be remote`

Эта ошибка появляется, когда локальный путь источника передан в `rsync` как
`E:/...`, и он ошибочно трактуется как `host:path`. В актуальной версии
`fs-syncher` локальный Windows-путь автоматически нормализуется в локальный формат
`/cygdrive/e/...`; если ошибка повторяется, обновите пакет до текущей версии.

#### Troubleshooting: `code 12` / `Permission denied (publickey)` на Windows

Для cwrsync-стека `rsync` и `ssh` должны работать в одном окружении. Если в системе
одновременно есть Windows OpenSSH и chocolatey-ssh, задайте транспорт явно:

```powershell
$env:HOME = "/cygdrive/c/Users/<user>"
$env:RSYNC_RSH = "/cygdrive/c/ProgramData/chocolatey/lib/rsync/tools/bin/ssh.exe"
bin\sync.bat "E:\Home" --dry-run --profile access
```

Если ключ защищён passphrase, используйте `ssh-agent` в выбранном окружении или
выделенный ключ для автоматизированных запусков.

### Формат `.fs-sync.toml`

Конфиг лежит **в корне синхронизируемого каталога**. Разбор — стандартный `tomllib`.

- `[defaults]` — значения по умолчанию для всех профилей;
- `[[sync]]` — профили зеркалирования (ПК → сервер, с зеркалированием удалений);
- `[[backup]]` — профили выгрузки-offload (передача + локальное удаление/архив).

Поля профиля:

| Поле | Назначение |
|------|------------|
| `name` | уникальное имя профиля (обязательно) |
| `local_root` | путь относительно конфига или абсолютный (обязателен, должен существовать) |
| `remote_root` | `user@host:/path`, `alias:/path` из `~/.ssh/config` или локальный путь (обязателен; локальный отсчитывается от каталога конфига) |
| `exclude` / `include` | списки gitignore-подобных паттернов |
| `delete` | зеркалить удаления (дефолт: `true` для sync, `false` для backup) |
| `dry_run` | дефолт `false` |
| `delete_threshold` / `delete_threshold_pct` | пороги delete-guard (по количеству — дефолт 100; по доле % — дефолт 25) |
| `force_delete` | снять delete-guard (дефолт `false`) |
| `checksum`, `compress`, `partial_progress` | опции передачи (bool) |
| `bwlimit` | ограничение полосы (строка) |
| `ssh_opts` | доп. опции `ssh` (список строк; только для SSH-целей) |
| `after_push` | только `[[backup]]`: `delete` / `archive` / `nothing` (дефолт `nothing`) |
| `verify` | только `[[backup]]`: сверка перед offload (дефолт `true`) |
| `archive_dir` | только `[[backup]]`: каталог архива (дефолт `<local_root>/../_fs-backup/<profile>/<YYYY-MM-DD>/`) |

Поле профиля перекрывает одноимённое из `[defaults]`. Валидация (ошибка → код 1 с
указанием профиля и поля): уникальность `name`; существование `local_root`; безопасный
`remote_root` (не корень `/`, непустой путь после `:`); корректный enum `after_push`;
типы полей.

### Правила include/exclude и трансляция в `rsync`

Сопоставление путей выполняет **сам `rsync`** через `--filter`-правила — он единственный
источник истины и для передачи, и для определения области offload (через
`rsync --list-only`). Своего матчера в режиме нет.

Синтаксис правил (gitignore-подобный): `*` (в пределах сегмента), `**` (cross-segment),
`?`, `[abc]`/`[a-z]`, завершающий `/` (только каталоги), ведущий/срединный `/` (якорь к
корню передачи). `exclude` исключает объект; `include` возвращает его (override).

`rsync` обрабатывает фильтры по принципу **«первое совпадение»**, поэтому порядок:

    1. безусловные артефакты:  - /.fs-sync.toml, - /.fs-log, - .env
    2. include (override):     + <pattern>
    3. exclude:                - <pattern>

Артефакты `.fs-sync.toml`, `.fs-log`, `.env` исключаются **всегда** и не возвращаются
никаким `include` (иначе меняющийся `.fs-log` сломал бы идемпотентность). Файл нельзя
вернуть из исключённого целиком каталога — `rsync` в него не заходит; возвращайте
каталог явно (`include = ["dir/"]`), затем точечные правила внутри.

### Offload (`[[backup]]`) и delete-guard

- **Offload-безопасность**: при `after_push` ∈ {`delete`, `archive`} локальный файл
  убирается **только после подтверждённой передачи** (`verify = true` сверяет повторным
  `rsync --dry-run --checksum`). Сбой передачи отменяет `after_push` целиком; `--dry-run`
  локальные файлы не трогает; частичный успех не трогает непереданное.
- **Сохранение якорных include-каталогов**: при `[[backup]]` опустевшие каталоги,
  явно заданные якорными include-правилами (например `**/Back/`), не удаляются после
  offload. Промежуточные/вложенные каталоги сохраняются только если заданы отдельным
  якорным include-паттерном (например `**/Back/**/Fold/**/`). Для одного и того же
  якоря сохраняется ближайший уровень: при `.../Back/Back` внутренний `Back` удаляется,
  если не задан отдельным более точным паттерном.

`local_root`/`remote_root`/`archive_dir` и `after_push = "archive"` — это внешний
контракт `fs-syncher`. Внутри режим по-прежнему использует свою модель профиля и
сборку команды `rsync`; семантика `rsync` и других библиотек не переопределяется.
- **Delete-guard**: серверные удаления выше порога (`delete_threshold` по количеству или
  `delete_threshold_pct` по доле) блокируются (код 3) до явного подтверждения
  (`--force-delete` или `force_delete = true`).

### Коды возврата

| Код | Условие |
|-----|---------|
| 0 | успех, включая «изменений нет» |
| 1 | ошибка запуска: нет каталога/`.fs-sync.toml`, ошибка валидации, нет `rsync` (или `ssh` при SSH-цели) |
| 2 | `rsync`/offload завершились ошибкой (передача неполная) |
| 3 | остановлено delete-guard (превышен порог удаления без подтверждения) |

Итог прогона — **наихудший** среди профилей по шкале `0 < 2 < 3` (код `1` — ошибка до
запуска профилей). Сбой записи `.fs-log` на код возврата не влияет.

### Уведомления (веб-хук) и `.env`

При наихудшем коде прогона `2` или `3` режим шлёт fire-and-forget веб-хук
(`POST {"text": ...}` с заголовком `Authorization: Bearer <токен>`, если токен задан;
сетевые ошибки гасятся и на код возврата не влияют). Конфигурация — в едином `.env`
проекта (`FS_TOOLS_HOME/.env`, фолбэк — `.env` в текущем каталоге), шаблон —
[`.env.example`](.env.example):

```dotenv
FSSYN_WEBHOOK_URL=https://example.com/hook
FSSYN_WEBHOOK_TOK=секретный-токен
```

Особенности: приоритет — переменные окружения процесса важнее значений из `.env`;
только `https://` URL (токен не уходит по нешифрованному каналу). Без `FSSYN_WEBHOOK_URL`
уведомления отключены; токен необязателен.

### Публичное API

```python
from pathlib import Path

from fs_tools.syncher import load_config, build_command, run_rsync

cfg = load_config(Path("/path/to/dir"))
profile = cfg.roll[0]
outcome = run_rsync(build_command(profile, dry_run=True, delete=profile.delete))
print(outcome.sent, outcome.deleted)
```

---

## Журнал `.fs-log`

Все режимы пишут единый журнал `.fs-log` в выбранный каталог (общий формат из
`fs_tools.shared.log`): блок с меткой времени, строками
`Инструмент: normalizer|checker|syncher`, `Режим: production|dry-run`,
`Результат:` и строками тела:

- нормализатор — последовательность событий в порядке выполнения:
  `old -> new`, `(КОНФЛИКТ) old -> new`, `(ОШИБКА) old -> new: <текст>` либо `(изменений нет)`;
- проверка — отсутствующие пути либо `(нарушений нет)`;
- синхронизация — операции с маркерами: `+ <путь>` (отправлено/обновлено),
  `- <путь>` (удалено на сервере), `>> <путь>` (выгружено и удалено/архивировано
  локально), а также `(КОНФЛИКТ)`/`(ОШИБКА)` по профилям — тоже в
  хронологическом порядке; при пустом результате пишется `(изменений нет)`.

Файл скрыт, создаётся при отсутствии и **дополняется** при повторных запусках
(намеренное исключение из идемпотентности), добавлен в `.gitignore`. Журнал пишется
и в `production`, и в `dry-run`; во втором случае фиксируется последовательность
dry-run-событий без применения изменений.

## Примеры

В [`examples/`](examples/) — три песочницы: `examples/normalizer/` (фикстуры по правилам
+ скрипты отката `reset.*`), `examples/checker/` (дерево с `.fs-check` и намеренно
отсутствующими путями) и `examples/syncher/` (источник + локальные приёмники, прогон без
сети, канонический `--dry-run`). Подробности — в README соответствующих секций.

## Аудит по правилам

Для стабильного аудита используй project skill `audit-governor` с фиксированными
режимами:

- `audit changed` — аудит внесенных правок;
- `audit full` — полный аудит проекта.

Рекомендуемые короткие запросы:

- `Запусти audit changed и доведи до полного green.`
- `Запусти audit full и доведи до полного green.`

Обязательный цикл проверок после каждой серии правок:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pylint --persistent=n --recursive=y src tests/*
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy --strict -p fs_tools
```

Цикл повторяется до полного green по всем четырем командам.

## Разработка

```bash
pytest                              # тесты
pylint --recursive=y src tests/*    # Pylint (полный охват src + tests/*)
ruff check .                        # линтер (в т.ч. порядок импортов, isort)
mypy --strict -p fs_tools           # проверка типов
python -m build                     # сборка sdist + wheel
```

Раскладка тестов зеркалит пакет: `tests/shared/`, `tests/normalizer/`, `tests/checker/`,
`tests/syncher/` (режим `--import-mode=importlib`). Код проходит `ruff` и
`mypy --strict` без замечаний. Интеграционные тесты режима синхронизации пропускаются,
если в системе нет `rsync`.
