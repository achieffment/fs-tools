"""Формирование текста стартового заголовка и итогового отчёта по профилям."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProfileReport:
    """Итог одного профиля для отчёта и журнала."""

    name: str
    kind: str
    code: int
    sent: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    offload: list[str] = field(default_factory=list)
    errlist: list[str] = field(default_factory=list)
    blocked: bool = False
    dry_run: bool = False

    def actions(self) -> list[str]:
        """Маркированные строки операций для журнала .fs-log.log (только выполненное)."""
        if self.blocked:
            return []
        ops = [f"+ {path}" for path in self.sent]
        ops = ops + [f"- {path}" for path in self.deleted]
        ops = ops + [f">> {path}" for path in self.offload]
        return ops


def format_header(root: Path, names: list[str], dry_run: bool) -> str:
    """Стартовая строка: профили, корень и режим прогона."""
    mode = "dry-run" if dry_run else "production"
    listed = ", ".join(names) if names else "—"
    return f"Каталог: {root}\nПрофили: {listed}\nРежим: {mode}"


def format_profile(report: ProfileReport) -> str:
    """Краткая сводка по профилю: передано/удалено/выгружено/ошибки или блокировка."""
    head = f"Профиль «{report.name}» ({report.kind}): "
    if report.blocked:
        return head + (
            f"остановлено защитой от массового удаления "
            f"(к удалению {len(report.deleted)}). Используйте --force-delete."
        )
    parts = [
        f"передано {len(report.sent)}",
        f"удалено {len(report.deleted)}",
        f"выгружено {len(report.offload)}",
        f"ошибок {len(report.errlist)}",
    ]
    return head + ", ".join(parts)


def format_report(root: Path, result: list[ProfileReport]) -> str:
    """Единый итоговый блок: двухстрочные статус и сводка."""
    worst = max((report.code for report in result), default=0)
    if worst == 0:
        status = f"ok. Синхронизация каталога {root} завершена успешно."
    elif worst == 3:
        status = "error. Синхронизация остановлена delete-guard."
    else:
        status = "error. Синхронизация завершена с ошибками rsync/offload."

    sent = sum(len(report.sent) for report in result)
    deleted = sum(len(report.deleted) for report in result)
    offload = sum(len(report.offload) for report in result)
    errcnt = sum(len(report.errlist) for report in result)
    blocked = sum(1 for report in result if report.blocked)

    lines = [f"Статус: {status}"]
    lines.append(
        f"Сводка: профилей: {len(result)}; передано: {sent}; удалено: {deleted}; "
        f"выгружено: {offload}; ошибок: {errcnt}; блокировок: {blocked}."
    )
    return "\n".join(lines)
