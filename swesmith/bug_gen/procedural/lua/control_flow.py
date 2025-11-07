import tree_sitter_lua as tslua

from swesmith.bug_gen.procedural.base import CommonPMs
from swesmith.bug_gen.procedural.lua.base import LuaProceduralModifier
from swesmith.constants import BugRewrite, CodeEntity
from tree_sitter import Language, Parser

LUA_LANGUAGE = Language(tslua.language())


class ControlIfElseInvertModifier(LuaProceduralModifier):
    """Swap if and else branches to create logical errors."""
    explanation: str = CommonPMs.CONTROL_IF_ELSE_INVERT.explanation
    name: str = CommonPMs.CONTROL_IF_ELSE_INVERT.name
    conditions: list = CommonPMs.CONTROL_IF_ELSE_INVERT.conditions
    min_complexity: int = -1  # Allow any complexity

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Swap if/else bodies in Lua code."""
        if not self.flip():
            return None

        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        
        modified_code = self._invert_if_else(code_entity.src_code, tree.root_node)
        
        if modified_code == code_entity.src_code:
            return None
        
        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
    
    def _invert_if_else(self, source_code: str, node) -> str:
        """Find and invert if/else statements."""
        modifications = []
        
        def collect_if_statements(n):
            if n.type == "if_statement":
                # Check if it has an else clause
                else_statement = None
                then_block = None
                
                for child in n.children:
                    if child.type == "block" and then_block is None:
                        then_block = child  # First block is the 'then' block
                    elif child.type == "else_statement":
                        else_statement = child
                
                # Only modify if we have both then and else
                if then_block and else_statement and self.flip():
                    # Find the else block within else_statement
                    else_block = None
                    for child in else_statement.children:
                        if child.type == "block":
                            else_block = child
                            break
                    
                    if else_block:
                        modifications.append((then_block, else_block))
            
            for child in n.children:
                collect_if_statements(child)
        
        collect_if_statements(node)
        
        # Apply modifications - swap the blocks
        modified_code = source_code
        for then_block, else_block in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            # Get the text content
            then_text = then_block.text.decode("utf-8")
            else_text = else_block.text.decode("utf-8")
            
            # Swap them
            modified_code = (
                modified_code[:then_block.start_byte] +
                else_text +
                modified_code[then_block.end_byte:else_block.start_byte] +
                then_text +
                modified_code[else_block.end_byte:]
            )
        
        return modified_code


class ControlShuffleLinesModifier(LuaProceduralModifier):
    """Shuffle statements within a function to break logic flow."""
    explanation: str = CommonPMs.CONTROL_SHUFFLE_LINES.explanation
    name: str = CommonPMs.CONTROL_SHUFFLE_LINES.name
    conditions: list = CommonPMs.CONTROL_SHUFFLE_LINES.conditions
    min_complexity: int = -1
    max_complexity: int = 15  # Don't shuffle very complex functions

    def modify(self, code_entity: CodeEntity) -> BugRewrite:
        """Shuffle statements in Lua function bodies."""
        if not self.flip():
            return None

        parser = Parser(LUA_LANGUAGE)
        tree = parser.parse(bytes(code_entity.src_code, "utf8"))
        
        modified_code = self._shuffle_statements(code_entity.src_code, tree.root_node)
        
        if modified_code == code_entity.src_code:
            return None
        
        return BugRewrite(
            rewrite=modified_code,
            explanation=self.explanation,
            strategy=self.name,
        )
    
    def _shuffle_statements(self, source_code: str, node) -> str:
        """Find function bodies and shuffle their statements."""
        modifications = []
        
        def collect_functions(n):
            if n.type == "function_declaration":
                # Find the function body block
                for child in n.children:
                    if child.type == "block":
                        statements = [c for c in child.children if c.type != "end"]
                        
                        # Only shuffle if we have 2+ statements
                        if len(statements) >= 2 and self.flip():
                            modifications.append((child, statements))
                        break
            
            for child in n.children:
                collect_functions(child)
        
        collect_functions(node)
        
        # Apply modifications - shuffle statements within blocks
        modified_code = source_code
        for block, statements in sorted(
            modifications, key=lambda x: x[0].start_byte, reverse=True
        ):
            # Get statement texts
            stmt_texts = [stmt.text.decode("utf-8") for stmt in statements]
            
            # Shuffle them
            shuffled_stmts = stmt_texts.copy()
            self.rand.shuffle(shuffled_stmts)
            
            # Reconstruct the block
            # Find the content between first and last statement
            if statements:
                first_start = statements[0].start_byte - block.start_byte
                last_end = statements[-1].end_byte - block.start_byte
                
                block_text = block.text.decode("utf-8")
                before = block_text[:first_start]
                after = block_text[last_end:]
                
                # Join shuffled statements with newlines
                new_block_text = before + "\n".join(shuffled_stmts) + after
                
                modified_code = (
                    modified_code[:block.start_byte] +
                    new_block_text +
                    modified_code[block.end_byte:]
                )
        
        return modified_code

