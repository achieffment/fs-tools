"""Режим односторонней синхронизации каталога с сервером (ПК → сервер) через rsync.

Читает .fs-syn.toml, транслирует правила include/exclude в фильтры rsync (сам rsync —
единственный источник истины для сопоставления путей), запускает rsync, разбирает
итог, пишет журнал .fs-log.log и шлёт веб-хук. Публичное API: импортируйте отсюда, а не
из подмодулей напрямую.
"""
from __future__ import annotations

from .config import (
    CONFIG_NAME,
    Config,
    ConfigError,
    Profile,
    is_ssh_target,
    load_config,
    parse_config,
    split_target,
)
from .ignore import ARTIFACTS, build_filters, filter_args
from .log import FS_LOG, write_fs_log
from .notify import load_webhook_config, send_webhook
from .offload import OffloadResult, run_offload
from .report import ProfileReport, format_header, format_profile, format_report
from .rsync import (
    DeletePlan,
    RsyncOutcome,
    build_command,
    build_listing,
    delete_preflight,
    parse_itemized,
    parse_listing,
    remote_object_count,
    rsync_available,
    run_rsync,
    source_files,
    ssh_available,
)
from .runner import main

__all__ = [
    "main",
    "Config",
    "ConfigError",
    "Profile",
    "CONFIG_NAME",
    "load_config",
    "parse_config",
    "split_target",
    "is_ssh_target",
    "ARTIFACTS",
    "build_filters",
    "filter_args",
    "RsyncOutcome",
    "DeletePlan",
    "build_command",
    "build_listing",
    "run_rsync",
    "parse_itemized",
    "parse_listing",
    "delete_preflight",
    "remote_object_count",
    "source_files",
    "rsync_available",
    "ssh_available",
    "OffloadResult",
    "run_offload",
    "ProfileReport",
    "format_header",
    "format_profile",
    "format_report",
    "FS_LOG",
    "write_fs_log",
    "load_webhook_config",
    "send_webhook",
]
