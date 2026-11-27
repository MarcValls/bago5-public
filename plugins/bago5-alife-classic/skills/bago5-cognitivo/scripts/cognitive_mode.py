"""Pure opt-in selector over the unchanged ADL lexical-focus component.

The caller resolves the user's explicit mode selection. This boolean is not
an authorization credential. This module has no I/O, storage or effect adapter.
"""
from __future__ import annotations

from typing import Any

from adl_focus import baseline_chat_context, build_chat_cognition


def context_for_turn(
    message: str, *, explicit_selection: bool = False
) -> dict[str, Any]:
    """Return ordinary context by default, or bounded ADL focus when selected.

    The complete original remains the caller's source. The focus helper only
    scans the first 8,000 characters for cues and must not replace that source.
    No selection or learned state is retained across calls.
    """
    if type(explicit_selection) is not bool:
        raise ValueError("EXPLICIT_SELECTION_MUST_BE_BOOLEAN")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("NONEMPTY_ORIGINAL_MESSAGE_REQUIRED")

    context = (
        build_chat_cognition(message)
        if explicit_selection
        else baseline_chat_context()
    )
    return {
        "mode": "cognitive" if explicit_selection else "ordinary",
        "context": context,
        "analyzed_prefix_chars": min(len(message), 8000) if explicit_selection else 0,
        "original_message_chars": len(message),
        "original_is_preserved_by": "caller",
        "execution_authority": False,
        "persistent_learning": False,
        "model_weights_changed": False,
        "memory_required": False,
    }
