"""Веб-хук schemer: тонкая обёртка над общей логикой `shared.notify`."""
from __future__ import annotations

import logging

from ..shared import notify as shared_notify

PREFIX = "FSSCH"
_LOG = logging.getLogger(__name__)

URL_KEY, TOK_KEY, TIMEOUT, load_webhook_config, send_webhook = shared_notify.make_mode_exports(
    prefix="FSSCH",
    logger=_LOG,
    timeout=2.0,
)
