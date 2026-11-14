"""Diagram generation package - UML and Draw.io."""

from .uml import DiagramFactory
from .uml import legacy_generator

__all__ = [
    "DiagramFactory",
    "legacy_generator",
]
