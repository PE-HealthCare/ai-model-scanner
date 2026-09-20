# src/p2_behavioral_risk/handoff.py
"""
D2 – Trusted Model Handoff (LOCKED)

This module handles the in‑process transfer of the trusted PyTorch model
from P1 (via scan_model.py) to P2. P2 must never reload the model itself.
"""

_TRUSTED_CONTEXT = None


def receive_trusted_model(context):
    """
    Receive the trusted model context from P1 (via scan_model.py).

    Args:
        context: The P1 TrustedModelContext object containing the model.

    Returns:
        The context itself (for chaining).

    Raises:
        ValueError: If context is None.
    """
    global _TRUSTED_CONTEXT
    if context is None:
        raise ValueError("Trusted model context cannot be None")
    _TRUSTED_CONTEXT = context
    return context


def get_trusted_model():
    """
    Retrieve the trusted model for P2 inference.

    Returns:
        The PyTorch model (nn.Module) from the stored context.

    Raises:
        RuntimeError: If no trusted model has been handed off.
    """
    if _TRUSTED_CONTEXT is None:
        raise RuntimeError(
            "No trusted P1 model context has been handed off to P2. "
            "Ensure scan_model.py calls receive_trusted_model() before P2 execution."
        )
    # Adjust the attribute name based on P1's actual context structure.
    # Common names: "model", "torch_model", "graph".
    # If you're unsure, inspect _TRUSTED_CONTEXT.__dict__ during debugging.
    return _TRUSTED_CONTEXT.model


def get_trusted_context():
    """
    Retrieve the full trusted context (if needed for metadata).

    Returns:
        The full context object.
    """
    if _TRUSTED_CONTEXT is None:
        raise RuntimeError("No trusted context available.")
    return _TRUSTED_CONTEXT