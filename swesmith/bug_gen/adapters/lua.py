"""
Lua code entity extractor using tree-sitter.
"""

import re
import tree_sitter_lua as tslua
from swesmith.constants import TODO_REWRITE, CodeEntity, CodeProperty
from tree_sitter import Language, Parser, Query, QueryCursor
import warnings

LUA_LANGUAGE = Language(tslua.language())


class LuaEntity(CodeEntity):
    def _analyze_properties(self):
        """Analyze the Lua AST node and set code properties as tags."""
        node = self.node
        
        # Core entity type - it's a function by definition
        self._tags.add(CodeProperty.IS_FUNCTION)
        
        # Walk the tree to find operations
        def walk_node(n):
            # Binary operations (arithmetic, comparison, logical)
            if n.type == "binary_expression":
                self._tags.add(CodeProperty.HAS_BINARY_OP)
                self._tags.add(CodeProperty.HAS_ARITHMETIC)
            
            # Assignment
            elif n.type in ["assignment", "local_variable_declaration"]:
                self._tags.add(CodeProperty.HAS_ASSIGNMENT)
            
            # Control flow
            elif n.type == "if_statement":
                self._tags.add(CodeProperty.HAS_IF)
                # Check if it has an else clause
                for child in n.children:
                    if child.type == "else_statement" or child.type == "elseif_statement":
                        self._tags.add(CodeProperty.HAS_IF_ELSE)
                        break
            
            elif n.type in ["for_statement", "while_statement", "repeat_statement"]:
                self._tags.add(CodeProperty.HAS_LOOP)
            
            # Function calls
            elif n.type == "function_call":
                self._tags.add(CodeProperty.HAS_FUNCTION_CALL)
            
            # Return statements
            elif n.type == "return_statement":
                self._tags.add(CodeProperty.HAS_RETURN)
            
            # Recursively walk children
            for child in n.children:
                walk_node(child)
        
        walk_node(node)
    @property
    def name(self) -> str:
        """Extract function name from Lua AST node."""
        # Query for regular function: function name(...)
        func_query = Query(
            LUA_LANGUAGE,
            "(function_declaration name: (identifier) @name)"
        )
        func_name = self._extract_text_from_first_match(func_query, self.node, "name")
        if func_name:
            return func_name
        
        # Query for method: function obj:method(...)
        method_query = Query(
            LUA_LANGUAGE,
            """
            (function_declaration
              name: (method_index_expression
                table: (identifier) @table
                method: (identifier) @method))
            """
        )
        matches = QueryCursor(method_query).matches(self.node)
        if matches:
            captures = matches[0][1]
            table = captures["table"][0].text.decode("utf-8")
            method = captures["method"][0].text.decode("utf-8")
            return f"{table}:{method}"
        
        # Query for dot notation: function obj.func(...)
        dot_query = Query(
            LUA_LANGUAGE,
            """
            (function_declaration
              name: (dot_index_expression
                table: (identifier) @table
                field: (identifier) @field))
            """
        )
        matches = QueryCursor(dot_query).matches(self.node)
        if matches:
            captures = matches[0][1]
            table = captures["table"][0].text.decode("utf-8")
            field = captures["field"][0].text.decode("utf-8")
            return f"{table}.{field}"
        
        # Query for local function: local function name(...)
        local_func_query = Query(
            LUA_LANGUAGE,
            "(function_declaration name: (identifier) @name)"
        )
        local_func_name = self._extract_text_from_first_match(local_func_query, self.node, "name")
        if local_func_name:
            return local_func_name
        
        return ""
    
    @property
    def signature(self) -> str:
        """Extract function signature (everything before the body)."""
        body_query = Query(
            LUA_LANGUAGE,
            "(function_declaration body: (block) @body)"
        )
        matches = QueryCursor(body_query).matches(self.node)
        if matches:
            body_node = matches[0][1]["body"][0]
            body_start_byte = body_node.start_byte - self.node.start_byte
            signature = self.node.text[:body_start_byte].strip().decode("utf-8")
            # Clean up whitespace
            signature = re.sub(r"\s+", " ", signature).strip()
            return signature
        return ""
    
    @property
    def stub(self) -> str:
        """Generate a stub with TODO comment."""
        return f"{self.signature}\n\t-- {TODO_REWRITE}\nend"
    
    @staticmethod
    def _extract_text_from_first_match(query, node, capture_name: str) -> str | None:
        """Extract text from tree-sitter query matches with None fallback."""
        matches = QueryCursor(query).matches(node)
        return matches[0][1][capture_name][0].text.decode("utf-8") if matches else None


def get_entities_from_file_lua(
    entities: list[LuaEntity],
    file_path: str,
    max_entities: int = -1,
) -> None:
    """
    Parse a .lua file and return up to max_entities functions.
    If max_entities < 0, collects them all.
    
    Args:
        entities: List to append LuaEntity objects to
        file_path: Path to the Lua file
        max_entities: Maximum number of entities to extract (-1 for unlimited)
    """
    parser = Parser(LUA_LANGUAGE)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
    except (OSError, UnicodeDecodeError):
        return
    
    tree = parser.parse(bytes(file_content, "utf-8"))
    root = tree.root_node
    lines = file_content.splitlines()
    
    def walk(node) -> None:
        # Stop if we've hit the limit
        if 0 <= max_entities == len(entities):
            return
        
        if node.type == "ERROR":
            warnings.warn(f"Error encountered parsing {file_path}")
            return
        
        # Match function declarations
        if node.type == "function_declaration":
            entities.append(_build_entity(node, lines, file_path))
            if 0 <= max_entities == len(entities):
                return
        
        for child in node.children:
            walk(child)
    
    walk(root)


def _build_entity(node, lines, file_path: str) -> LuaEntity:
    """
    Turns a Tree-sitter node into a LuaEntity object.
    """
    # start_point/end_point are (row, col) zero-based
    start_row, _ = node.start_point
    end_row, _ = node.end_point
    
    # Slice out the raw lines
    snippet = lines[start_row : end_row + 1]
    
    # Detect indent on first line
    first = snippet[0]
    m = re.match(r"^(?P<indent>[\t ]*)", first)
    indent_str = m.group("indent")
    # Tabs count as size=1, else use count of spaces, fallback to 4
    indent_size = 1 if "\t" in indent_str else (len(indent_str) or 4)
    indent_level = len(indent_str) // indent_size
    
    # Dedent each line
    dedented = []
    for line in snippet:
        if len(line) >= indent_level * indent_size:
            dedented.append(line[indent_level * indent_size :])
        else:
            dedented.append(line.lstrip("\t "))
    
    return LuaEntity(
        file_path=file_path,
        indent_level=indent_level,
        indent_size=indent_size,
        line_start=start_row + 1,
        line_end=end_row + 1,
        node=node,
        src_code="\n".join(dedented),
    )

