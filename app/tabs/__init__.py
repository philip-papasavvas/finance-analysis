"""Tab modules for portfolio viewer."""

from app.tabs.current_holdings import render_current_holdings_tab
from app.tabs.funds_list import render_funds_list_tab
from app.tabs.transaction_history import render_transaction_history_tab
from app.tabs.price_history import render_price_history_tab
from app.tabs.mapping_status import render_mapping_status_tab

__all__ = [
    "render_current_holdings_tab",
    "render_funds_list_tab",
    "render_transaction_history_tab",
    "render_price_history_tab",
    "render_mapping_status_tab",
]
