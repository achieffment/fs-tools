# examples — тестовое дерево для проверки структуры

Песочница для ручного прогона проверки структуры (`fs-checker`). Дерево воспроизводит раздел
`Activities/Web` доменной структуры хранилища `Home`: занятия с `Projects`
и `Resources`, категории `Addl`/`Self`/`Work`, организации внутри `Work`, обычные
и архивные (`_Archive`) проекты с папками `Back`/`Data` и файлом `Data/project.md`.

Утилита **не меняет структуру** дерева: запуск ничего не создаёт, не переименовывает
и не удаляет. Поэтому reset-скриптов здесь нет. Единственная запись — журнал
`.fs-log` в этом каталоге (т.к. путей не хватает): он скрыт, в репозиторий не
попадает (`.gitignore`) и на сам отчёт не влияет.

Часть путей **намеренно отсутствует**, чтобы прогон показывал нарушения и по
папкам, и по файлам. Для `_Archive` в правилах показаны и позитивные шаблоны с
`**`, и short-negation `!_Archive`: в этой песочнице архивные ветки намеренно
исключаются из итоговой проверки.

> Пустые каталоги git не хранит, поэтому в листовых папках лежит файл-заглушка
> `.gitkeep`. Он скрыт (имя на `.`) и на проверку не влияет: обходом такие имена
> пропускаются, а мандат сверяется по самому каталогу (`is_dir()`/`exists()`).

## Как пользоваться

```bash
# установленная команда; утилита спросит каталог интерактивно
fs-checker
# и укажите папку examples/checker

# либо сразу аргументом, без диалога:
fs-checker examples/checker

# то же через обёртки bin/ (создают .venv и editable-установку при первом запуске):
bin/check.sh         # Linux/macOS (терминал)
bin/check.command    # macOS (двойной клик в Finder)
bin/check.bat        # Windows
```

## Файл правил

[`examples/checker/.fs-chk`](.fs-chk) демонстрирует все возможности формата:

- **корневая цепочка** литералов `/Activities`, `/Activities/Web`,
  `/Activities/Web/Projects` — фиксированные каталоги, обязательные сами по себе
  (без них пропажа целой ветки осталась бы незамеченной);
- **подстановки** `*` (`/Activities/*/Projects`) и `**`
  (`/Activities/Web/Projects/**/_Archive/*/Back`) — эти `_Archive`-правила
  сохранены как демонстрация формата;
- **строго каталог** — завершающий `/` (`/Activities/Web/Projects/Addl/`): мандат
  проверяется как `is_dir()`;
- **мандат-файл** без `/` (`…/Work/*/*/Data/project.md`): проверка `exists()`
  (файл или папка);
- **негативы `!` через ordered pathspec**:
  - short basename-паттерн (например, `!_Archive`);
  - path-based исключение конкретного пути (например, `!/Workspace/Code/Projects`);
  - path-based исключение по маске (например, `!/Code/PHP/**`);
  - порядок строк учитывается (`last-match-wins` для конфликтующих паттернов).
  - re-include не используется: в checker `!!...` схлопывается до `!...`.

## Ожидаемый результат

На этом дереве прогон сообщает ровно **4** отсутствующих пути:

```text
Отсутствуют пути (4):
  Activities/3D/Resources
  Activities/Web/Projects/Addl/safegrid.example/Data
  Activities/Web/Projects/Self/personal.example/Back
  Activities/Web/Projects/Work/Fabrikam/widgets.example/Data/project.md
Статус: warn. Найдены отсутствующие пути.
Сводка: проверено правил: 17; найдено каталогов-кандидатов: 22; отсутствует: 4.
```

Как читать результат:

| Путь | Почему попал в отчёт |
|------|----------------------|
| `Activities/3D/Resources` | у занятия `3D` есть `Projects`, но нет `Resources` (`/Activities/*/Resources`) |
| `…/Addl/safegrid.example/Data` | обычный проект `safegrid.example`: `Back` есть, `Data` нет (`Addl/*/Data`) |
| `…/Self/personal.example/Back` | обычный проект `personal.example`: `Data` есть, `Back` нет (`Self/*/Back`) |
| `…/Work/Fabrikam/widgets.example/Data/project.md` | проект есть, `Data` есть, но обязательного файла `project.md` нет (мандат-файл) |

Чего в отчёте **нет** (и это правильно):

- любые ветки `_Archive` (включая `Addl/_Archive/...` и
  `Work/Fabrikam/_Archive/...`) — отсекаются коротким pathspec-паттерном
  `!_Archive`, поэтому архивные `Back`/`Data`/`project.md` не требуются, даже
  при наличии демонстрационных `_Archive`-правил выше;
- `Activities/3D/Projects` и любые `Back`/`Data`/`project.md` у существующих
  проектов (`crm.example.com`, `widgets.example` — кроме его `project.md`, `wheels.example`) —
  они на месте.

Чтобы увидеть «всё на месте» (код возврата `0`), создайте недостающие папки/файлы
вручную (например, `mkdir Activities/3D/Resources`) и повторите запуск — утилита
ничего на диске не меняет сама.
