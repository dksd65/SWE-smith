from abc import ABC
from swesmith.bug_gen.procedural.base import ProceduralModifier


class LuaProceduralModifier(ProceduralModifier, ABC):
    """Base class for Lua-specific procedural modifications."""

