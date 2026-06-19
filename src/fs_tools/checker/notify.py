"""Веб-хук checker: тонкая обёртка над общей логикой `shared.notify`."""
from ..shared import notify as shared_notify

URL_KEY, TOK_KEY, TIMEOUT, load_webhook_config, send_webhook = shared_notify.make_mode_exports(
    url_key="FSCHK_WEBHOOK_URL",
    tok_key="FSCHK_WEBHOOK_TOK",
    logger_name=__name__,
    timeout=2.0,
)
