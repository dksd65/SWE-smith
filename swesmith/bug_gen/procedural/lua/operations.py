import tree_sitter_lua as tslua

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.lua.base import LuaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Language, Parser

LUA_LANGUAGE = Language(tslua.language())

# Mapping of Lua binary operators to their alternatives
FLIPPED_OPERATORS = {
    "+": "-",
    "-": "+",
    "*": "/",
    "/": "*",
    "%": "*",  # Modulo to multiplication
    "//": "/",  # Floor division to division
    "^": "*",   # Power to multiplication
    "==": "~=",
    "~=": "==",
    "<": ">",
    "<=": ">=",
    ">": "<",
    ">=": "<=",
    "and": "or",
    "or": "and",
    "..": "+",  # String concatenation to addition (common mistake)
}

# Operator groups for systematic changes
ARITHMETIC_OPS = ["+", "-", "*", "/", "//", "%", "^"]
COMPARISON_OPS = ["==", "~=", "<", "<=", ">", ">="]
LOGICAL_OPS = ["and", "or"]
STRING_OPS = [".."]


class OperationChangeModifier(LuaProceduralModifier):
    explanation: str = CommonPMs.OPERATION_CHANGE.explanation
    name: str = CommonPMs.OPERATION_CHANGE.name
    conditions: list = CommonPMs.OPERATION_CHANGE.conditions
    min_complexity: int = -1  # Allow any complexity for Lua (complexity not implemented yet)

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply operation changes to Lua binary expressions."""
        if not self.flip():
            return None

        # Parse the code
        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find and modify binary operations
        modified_code = self._change_operations(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_operations(self, source_code: str, node) -> str:
        """Recursively find and change binary operations."""
        modifications = []

        def collect_binary_ops(n):
            # Lua tree-sitter uses "binary_expression" node type
            if n.type == "binary_expression":
                # Find the operator - it's usually the middle child
                if len(n.children) >= 3:
                    operator_node = n.children[1]  # Middle child is the operator
                    if operator_node and self.flip():
                        op = operator_node.text.decode("utf-8")
                        new_op = self._get_alternative_operator(op)
                        if new_op != op:
                            modifications.append((operator_node, new_op))

            for child in n.children:
                collect_binary_ops(child)

        collect_binary_ops(node)

        # Apply modifications from right to left to preserve positions
        modified_code = source_code
        for operator_node, new_op in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            start_byte = operator_node.start_byte
            end_byte = operator_node.end_byte
            modified_code = (
                modified_code[:start_byte] + new_op + modified_code[end_byte:]
            )

        return modified_code

    def _get_alternative_operator(self, op: str) -> str:
        """Get an alternative operator from the same category."""
        if op in ARITHMETIC_OPS:
            return self.rand.choice(ARITHMETIC_OPS)
        elif op in COMPARISON_OPS:
            return self.rand.choice(COMPARISON_OPS)
        elif op in LOGICAL_OPS:
            return self.rand.choice(LOGICAL_OPS)
        elif op in STRING_OPS:
            return self.rand.choice(ARITHMETIC_OPS)  # Confuse string with arithmetic
        return op


class OperationFlipOperatorModifier(LuaProceduralModifier):
    explanation: str = CommonPMs.OPERATION_FLIP_OPERATOR.explanation
    name: str = CommonPMs.OPERATION_FLIP_OPERATOR.name
    conditions: list = CommonPMs.OPERATION_FLIP_OPERATOR.conditions
    min_complexity: int = -1  # Allow any complexity for Lua (complexity not implemented yet)

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply operator flipping to Lua binary expressions."""
        if not self.flip():
            return None

        # Parse the code
        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find and flip binary operations
        modified_code = self._flip_operators(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _flip_operators(self, source_code: str, node) -> str:
        """Recursively find and flip binary operations."""
        modifications = []

        def collect_binary_ops(n):
            if n.type == "binary_expression":
                if len(n.children) >= 3:
                    operator_node = n.children[1]
                    if operator_node and self.flip():
                        op = operator_node.text.decode("utf-8")
                        if op in FLIPPED_OPERATORS:
                            modifications.append((operator_node, FLIPPED_OPERATORS[op]))

            for child in n.children:
                collect_binary_ops(child)

        collect_binary_ops(node)

        # Apply modifications from right to left to preserve positions
        modified_code = source_code
        for operator_node, new_op in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            start_byte = operator_node.start_byte
            end_byte = operator_node.end_byte
            modified_code = (
                modified_code[:start_byte] + new_op + modified_code[end_byte:]
            )

        return modified_code


class OperationChangeConstantsModifier(LuaProceduralModifier):
    explanation: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.explanation
    name: str = CommonPMs.OPERATION_CHANGE_CONSTANTS.name
    conditions: list = CommonPMs.OPERATION_CHANGE_CONSTANTS.conditions
    min_complexity: int = -1  # Allow any complexity for Lua (complexity not implemented yet)

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Apply constant changes to Lua binary expressions."""
        if not self.flip():
            return None

        # Parse the code
        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))

        # Find and modify constants
        modified_code = self._change_constants(code_entity.src_code, tree.root_node)

        if modified_code == code_entity.src_code:
            return None

        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )

    def _change_constants(self, source_code: str, node) -> str:
        """Recursively find and modify number constants."""
        modifications = []

        def collect_constants(n):
            if n.type == "number":
                if self.flip():
                    try:
                        value_text = n.text.decode("utf-8")
                        # Try to parse as integer first, then float
                        if "." in value_text or "e" in value_text.lower():
                            value = float(value_text)
                            delta = self.rand.choice([-0.1, 0.1, -1.0, 1.0])
                            new_value = str(value + delta)
                        else:
                            value = int(value_text)
                            new_value = str(value + self.rand.choice([-1, 1]))
                        modifications.append((n, new_value))
                    except ValueError:
                        pass  # Skip invalid number literals

            for child in n.children:
                collect_constants(child)

        collect_constants(node)

        # Apply modifications from right to left to preserve positions
        modified_code = source_code
        for const_node, new_value in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            start_byte = const_node.start_byte
            end_byte = const_node.end_byte
            modified_code = (
                modified_code[:start_byte] + new_value + modified_code[end_byte:]
            )

        return modified_code

