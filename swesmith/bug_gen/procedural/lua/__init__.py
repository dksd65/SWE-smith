from swesmith.bug_gen.procedural.base import ProceduralModifier
from swesmith.bug_gen.procedural.lua.control_flow import (
    ControlIfElseInvertModifier,
    ControlShuffleLinesModifier,
)
from swesmith.bug_gen.procedural.lua.operations import (
    OperationChangeModifier,
    OperationFlipOperatorModifier,
    OperationChangeConstantsModifier,
)
from swesmith.bug_gen.procedural.lua.remove import (
    RemoveAssignModifier,
    RemoveConditionalModifier,
    RemoveLoopModifier,
)

MODIFIERS_LUA: list[ProceduralModifier] = [
    # Operations
    OperationChangeModifier(likelihood=0.6),
    OperationFlipOperatorModifier(likelihood=0.6),
    OperationChangeConstantsModifier(likelihood=0.6),
    # Control flow
    ControlIfElseInvertModifier(likelihood=0.8),
    ControlShuffleLinesModifier(likelihood=0.5),
    # Remove
    RemoveConditionalModifier(likelihood=0.6),
    RemoveAssignModifier(likelihood=0.6),
    RemoveLoopModifier(likelihood=0.5),
]
