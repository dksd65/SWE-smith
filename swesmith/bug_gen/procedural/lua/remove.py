import tree_sitter_lua as tslua

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.lua.base import LuaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Language, Parser

LUA_LANGUAGE = Language(tslua.language())


class RemoveConditionalModifier(LuaProceduralModifier):
    """Remove if statements, keeping only one branch."""
    explanation: str = CommonPMs.REMOVE_CONDITIONAL.explanation
    name: str = CommonPMs.REMOVE_CONDITIONAL.name
    conditions: list = CommonPMs.REMOVE_CONDITIONAL.conditions
    min_complexity: int = -1

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove if statements from Lua code."""
        if not self.flip():
            return None

        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        
        modified_code = self._remove_conditionals(code_entity.src_code, tree.root_node)
        
        if modified_code == code_entity.src_code:
            return None
        
        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
    
    def _remove_conditionals(self, source_code: str, node) -> str:
        """Find and remove if statements, keeping one branch."""
        modifications = []
        
        def collect_if_statements(n):
            if n.type == "if_statement" and self.flip():
                # Find the then block (first block child)
                then_block = None
                for child in n.children:
                    if child.type == "block":
                        then_block = child
                        break
                
                if then_block:
                    # Extract just the statements inside the block
                    block_text = then_block.text.decode("utf-8")
                    # Remove the outer block structure, keep inner statements
                    # This is a simplified approach - keeps the whole block content
                    modifications.append((n, block_text))
            
            for child in n.children:
                collect_if_statements(child)
        
        collect_if_statements(node)
        
        # Apply modifications
        modified_code = source_code
        for if_node, replacement in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            modified_code = (
                modified_code[:if_node.start_byte] +
                replacement +
                modified_code[if_node.end_byte:]
            )
        
        return modified_code


class RemoveAssignModifier(LuaProceduralModifier):
    """Remove local variable assignments."""
    explanation: str = CommonPMs.REMOVE_ASSIGNMENT.explanation
    name: str = CommonPMs.REMOVE_ASSIGNMENT.name
    conditions: list = CommonPMs.REMOVE_ASSIGNMENT.conditions
    min_complexity: int = -1

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove assignment statements from Lua code."""
        if not self.flip():
            return None

        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        
        modified_code = self._remove_assignments(code_entity.src_code, tree.root_node)
        
        if modified_code == code_entity.src_code:
            return None
        
        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
    
    def _remove_assignments(self, source_code: str, node) -> str:
        """Find and remove local variable declarations."""
        modifications = []
        
        def collect_assignments(n):
            # Lua has "variable_declaration" for local variables
            if n.type == "variable_declaration" and self.flip():
                # Check if it's a local declaration
                is_local = False
                for child in n.children:
                    if child.type == "local":
                        is_local = True
                        break
                
                if is_local:
                    modifications.append(n)
            
            for child in n.children:
                collect_assignments(child)
        
        collect_assignments(node)
        
        # Apply modifications - remove the entire statement including newline
        modified_code = source_code
        for assignment in sorted(modifications, key=lambda x: x.start_byte, reverse=True):
            # Try to remove the entire line including trailing newline
            start = assignment.start_byte
            end = assignment.end_byte
            
            # Check if there's a newline after
            if end < len(modified_code) and modified_code[end] == '\n':
                end += 1
            
            modified_code = modified_code[:start] + modified_code[end:]
        
        return modified_code


class RemoveLoopModifier(LuaProceduralModifier):
    """Remove loop constructs (for, while, repeat)."""
    explanation: str = CommonPMs.REMOVE_LOOP.explanation
    name: str = CommonPMs.REMOVE_LOOP.name
    conditions: list = CommonPMs.REMOVE_LOOP.conditions
    min_complexity: int = -1

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Remove loop statements from Lua code."""
        if not self.flip():
            return None

        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        
        modified_code = self._remove_loops(code_entity.src_code, tree.root_node)
        
        if modified_code == code_entity.src_code:
            return None
        
        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
    
    def _remove_loops(self, source_code: str, node) -> str:
        """Find and remove loop constructs."""
        modifications = []
        
        def collect_loops(n):
            if n.type in ["for_statement", "while_statement", "repeat_statement"] and self.flip():
                modifications.append(n)
            
            for child in n.children:
                collect_loops(child)
        
        collect_loops(node)
        
        # Apply modifications - remove entire loop
        modified_code = source_code
        for loop in sorted(modifications, key=lambda x: x.start_byte, reverse=True):
            start = loop.start_byte
            end = loop.end_byte
            
            # Try to include trailing newline
            if end < len(modified_code) and modified_code[end] == '\n':
                end += 1
            
            modified_code = modified_code[:start] + modified_code[end:]
        
        return modified_code

