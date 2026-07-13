"""Трансляция правил include/exclude из .fs-syn.toml в фильтры rsync.

Сопоставление путей выполняет сам rsync (опции `--filter`) — он же единственный
источник истины и для передачи, и для определения области offload (через
`rsync --list-only`). Поэтому здесь только детерминированная сборка правил, без
отдельного матчера.

Синтаксис правил — фильтры rsync (gitignore-подобные): `*` (в пределах сегмента),
`**` (cross-segment), `?`, `[abc]`/`[a-z]`, завершающий `/` (только каталоги),
ведущий/срединный `/` (якорь к корню передачи = `local_root`). `exclude` исключает
объект; `include` возвращает его (override) и выигрывает над `exclude`.

rsync обрабатывает фильтры по принципу «первое совпадение», поэтому порядок правил
инвертирован относительно gitignore («последнее совпадение»):
  1. безусловные артефакты (исключаются всегда, не возвращаются никаким include);
  2. include (`+ <pattern>`);
  3. exclude (`- <pattern>`).

Известное ограничение: файл нельзя вернуть из исключённого целиком каталога — rsync
в него не заходит. Возвращайте каталог явно (`!`-эквивалент: `include = ["dir/"]`),
затем точечные правила внутри.

Служебные артефакты (`.fs-syn.toml`, `.fs-log.log`, `.env`) исключаются всегда: иначе
они уйдут на сервер, а меняющийся `.fs-log.log` сломает идемпотентность (повторный прогон
давал бы вечный diff).
"""
from __future__ import annotations

# Имена собственных артефактов утилиты — никогда не передаются на сервер.
ARTIFACTS: tuple[str, ...] = (".fs-syn.toml", ".fs-log.log", ".env")


def auto_exclude_filters() -> list[str]:
    """rsync-фильтры безусловного исключения артефактов (идут первыми → выигрывают)."""
    # Конфиг и журнал — на верхушке корня передачи; .env исключается на любой глубине.
    return ["- /.fs-syn.toml", "- /.fs-log.log", "- .env"]


def build_filters(exclude: list[str], include: list[str]) -> list[str]:
    """Список правил для rsync `--filter` из exclude/include профиля.

    Порядок (из-за «первое совпадение» в rsync): безусловные артефакты, затем
    include (`+`), затем exclude (`-`). Так артефакты не вернуть никаким include, а
    пользовательский include перекрывает exclude.
    """
    rules: list[str] = []
    rules = rules + auto_exclude_filters()
    rules = rules + [f"+ {pat}" for pat in include]
    rules = rules + [f"- {pat}" for pat in exclude]
    return rules


def filter_args(exclude: list[str], include: list[str]) -> list[str]:
    """Готовые аргументы командной строки rsync: `--filter=<rule>` для каждого правила."""
    return [f"--filter={rule}" for rule in build_filters(exclude, include)]
