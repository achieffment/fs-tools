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
    offloaded: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    blocked: bool = False

    def operations(self) -> list[str]:
        """Маркированные строки операций для журнала .fs-log (только выполненное)."""
        ops = [f"+ {path}" for path in self.sent]
        ops += [f"- {path}" for path in self.deleted]
        ops += [f">> {path}" for path in self.offloaded]
        return ops


def format_header(root: Path, names: list[str], dry_run: bool) -> str:
    """Стартовая строка: профили, корень и режим прогона."""
    mode = "dry-run (без изменений)" if dry_run else "боевой"
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
        f"выгружено {len(report.offloaded)}",
        f"ошибок {len(report.errors)}",
    ]
    return head + ", ".join(parts)


def format_report(root: Path, reports: list[ProfileReport]) -> str:
    """Полный итоговый отчёт по всем профилям."""
    lines = [f"Итог ({root}):"]
    for report in reports:
        lines.append("  " + format_profile(report))
    return "\n".join(lines)
