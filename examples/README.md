# examples — тестовое дерево для проверки структуры

Песочница для ручного прогона `fs-checker`. Дерево воспроизводит раздел
`Activities/Web` доменной структуры хранилища `Home`: занятия с `Projects`
и `Resources`, категории `Addl`/`Self`/`Work`, организации внутри `Work`, обычные
и архивные (`_Archive`) проекты с папками `Back`/`Data` и файлом `Data/project.md`.

Утилита **не меняет структуру** дерева: запуск ничего не создаёт, не переименовывает
и не удаляет. Поэтому reset-скриптов здесь нет. Единственная запись — журнал
`.fs-log` в этом каталоге (т.к. путей не хватает): он скрыт, в репозиторий не
попадает (`.gitignore`) и на сам отчёт не влияет.

Часть путей **намеренно отсутствует**, чтобы прогон показывал нарушения и по
папкам, и по файлам, а ветка `_Archive` демонстрировала исключение из подстановок.

> Пустые каталоги git не хранит, поэтому в листовых папках лежит файл-заглушка
> `.gitkeep`. Он скрыт (имя на `.`) и на проверку не влияет: обходом такие имена
> пропускаются, а мандат сверяется по самому каталогу (`is_dir()`/`exists()`).

## Как пользоваться

```bash
# из корня проекта; утилита спросит каталог интерактивно
./check.sh        # Linux/macOS (терминал)
./check.command   # macOS (двойной клик в Finder)
./check.bat       # Windows
# и укажите папку examples
```

Альтернатива — программно: `python check_fs.py` (каталог выбирается интерактивно).

## Файл правил

[`examples/.fs-rule`](.fs-rule) демонстрирует все возможности формата:

- **корневая цепочка** литералов `/Activities`, `/Activities/Web`,
  `/Activities/Web/Projects` — фиксированные каталоги, обязательные сами по себе
  (без них пропажа целой ветки осталась бы незамеченной);
- **подстановки** `*` (`/Activities/*/Projects`) и `**`
  (`/Activities/Web/Projects/**/_Archive/*/Back`);
- **строго каталог** — завершающий `/` (`/Activities/Web/Projects/Addl/`): мандат
  проверяется как `is_dir()`;
- **мандат-файл** без `/` (`…/Work/*/*/Data/project.md`): проверка `exists()`
  (файл или папка);
- **негатив** `!_Archive` — исключает служебный `_Archive` из подстановок `*`/`**`.

## Ожидаемый результат

На этом дереве прогон сообщает ровно **7** отсутствующих путей:

```text
Отсутствуют пути (7):
  Activities/3D/Resources
  Activities/Web/Projects/Addl/_Archive/aero.example/Data
  Activities/Web/Projects/Addl/safegrid.example/Data
  Activities/Web/Projects/Self/personal.example/Back
  Activities/Web/Projects/Work/Fabrikam/_Archive/acoustic.example/Back
  Activities/Web/Projects/Work/Fabrikam/_Archive/acoustic.example/Data
  Activities/Web/Projects/Work/Fabrikam/widgets.example/Data/project.md
Проверено правил: 17. Найдено каталогов-кандидатов: 26. Отсутствует: 7.
```

Как читать результат:

| Путь | Почему попал в отчёт |
|------|----------------------|
| `Activities/3D/Resources` | у занятия `3D` есть `Projects`, но нет `Resources` (`/Activities/*/Resources`) |
| `…/Addl/safegrid.example/Data` | обычный проект `safegrid.example`: `Back` есть, `Data` нет (`Addl/*/Data`) |
| `…/Self/personal.example/Back` | обычный проект `personal.example`: `Data` есть, `Back` нет (`Self/*/Back`) |
| `…/Work/Fabrikam/widgets.example/Data/project.md` | проект есть, `Data` есть, но обязательного файла `project.md` нет (мандат-файл) |
| `…/Addl/_Archive/aero.example/Data` | архивный проект проверяется правилом `**/_Archive/*/Data` (литерал `_Archive`); `Back` есть, `Data` нет |
| `…/Work/Fabrikam/_Archive/acoustic.example/Back` и `/Data` | архивный проект без `Back`/`Data` — оба сообщаются (`**/_Archive/*/…`) |

Чего в отчёте **нет** (и это правильно):

- `Activities/Web/Projects/Addl/_Archive/Back` — `*` в `Addl/*/Back` выбрал
  `_Archive`, но негатив `!_Archive` его отбросил (служебный каталог, не проект);
- `Activities/Web/Projects/Work/Fabrikam/_Archive/…` для правил `Work/*/*/Back|Data` и
  `…/Data/project.md` — `_Archive` стоит на **промежуточной** `*`-позиции (позиция
  проекта), но всё равно отсекается негативом, поэтому `Back`/`Data`/`project.md`
  там не требуются;
- `Activities/3D/Projects` и любые `Back`/`Data`/`project.md` у существующих
  проектов (`crm.example.com`, `widgets.example` — кроме его `project.md`, `wheels.example`) —
  они на месте.

Чтобы увидеть «всё на месте» (код возврата `0`), создайте недостающие папки/файлы
вручную (например, `mkdir Activities/3D/Resources`) и повторите запуск — утилита
ничего на диске не меняет сама.
