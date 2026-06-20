"""Веб-хук syncher: тонкая обёртка над общей логикой `shared.notify`."""
from __future__ import annotations

import logging

from ..shared import notify as shared_notify

PREFIX = "FSSYN"
_LOG = logging.getLogger(__name__)

URL_KEY, TOK_KEY, TIMEOUT, load_webhook_config, send_webhook = shared_notify.make_mode_exports(
    prefix="FSSYN",
    logger=_LOG,
    timeout=2.0,
)
