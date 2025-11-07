import pytest
import re
import warnings

from swesmith.bug_gen.adapters.lua import (
    get_entities_from_file_lua,
    LuaEntity,
)


@pytest.fixture
def test_lua_file(tmp_path):
    """Create a test Lua file with various function types."""
    test_file = tmp_path / "test.lua"
    test_code = """
-- Test Lua file
function greet(name)
    print("Hello, " .. name)
    return name
end

local function calculate(x, y)
    local result = x + y
    return result
end

function MyClass:method(arg)
    self.value = arg
    return self.value
end

function MyModule.utility(data)
    return #data
end

local function helper()
    -- Helper function
end
"""
    test_file.write_text(test_code)
    return str(test_file)


@pytest.fixture
def entities(test_lua_file):
    entities = []
    get_entities_from_file_lua(entities, test_lua_file)
    return entities


def test_get_entities_from_file_lua_count(entities):
    """Test that all functions are extracted."""
    assert len(entities) == 5


def test_get_entities_from_file_lua_max(test_lua_file):
    """Test max_entities limit."""
    entities = []
    get_entities_from_file_lua(entities, test_lua_file, 3)
    assert len(entities) == 3


def test_get_entities_from_file_lua_unreadable():
    """Test handling of non-existent file."""
    entities = []
    get_entities_from_file_lua(entities, "non-existent-file.lua")
    # Should return silently without error
    assert len(entities) == 0


def test_get_entities_from_file_lua_no_functions(tmp_path):
    """Test file with no functions."""
    no_functions_file = tmp_path / "no_functions.lua"
    no_functions_file.write_text("-- there are no functions here\nlocal x = 5")
    entities = []
    get_entities_from_file_lua(entities, str(no_functions_file))
    assert len(entities) == 0


def test_get_entities_from_file_lua_malformed(tmp_path):
    """Test handling of malformed Lua code."""
    malformed_file = tmp_path / "malformed.lua"
    malformed_file.write_text("function (malformed")
    entities = []
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        get_entities_from_file_lua(entities, str(malformed_file))
        # tree-sitter should handle malformed code gracefully
        # May or may not produce warnings


def test_get_entities_from_file_lua_names(entities):
    """Test that function names are extracted correctly."""
    names = [e.name for e in entities]
    assert "greet" in names
    assert "calculate" in names
    assert "MyClass:method" in names  # Method notation
    assert "MyModule.utility" in names  # Dot notation
    assert "helper" in names


def test_get_entities_from_file_lua_regular_function(entities):
    """Test regular function extraction."""
    greet = [e for e in entities if e.name == "greet"][0]
    assert greet.line_start == 3
    assert greet.line_end == 6
    assert "greet(name)" in greet.signature


def test_get_entities_from_file_lua_local_function(entities):
    """Test local function extraction."""
    calculate = [e for e in entities if e.name == "calculate"][0]
    assert calculate.line_start == 8
    assert calculate.line_end == 11
    assert "local function calculate" in calculate.signature


def test_get_entities_from_file_lua_method(entities):
    """Test method notation extraction (colon)."""
    method = [e for e in entities if e.name == "MyClass:method"][0]
    assert method.line_start == 13
    assert method.line_end == 16
    assert "MyClass:method" in method.signature


def test_get_entities_from_file_lua_dot_notation(entities):
    """Test dot notation extraction."""
    utility = [e for e in entities if e.name == "MyModule.utility"][0]
    assert utility.line_start == 18
    assert utility.line_end == 20
    assert "MyModule.utility" in utility.signature


def test_get_entities_from_file_lua_indentation(entities):
    """Test that indentation is detected correctly."""
    greet = [e for e in entities if e.name == "greet"][0]
    assert greet.indent_level == 0
    assert greet.indent_size == 4


def test_get_entities_from_file_lua_source_code(entities):
    """Test that source code is extracted correctly."""
    greet = [e for e in entities if e.name == "greet"][0]
    assert "function greet(name)" in greet.src_code
    assert 'print("Hello, " .. name)' in greet.src_code
    assert "return name" in greet.src_code
    assert "end" in greet.src_code


def test_get_entities_from_file_lua_stub(entities):
    """Test that stubs are generated correctly."""
    greet = [e for e in entities if e.name == "greet"][0]
    stub = greet.stub
    assert "function greet(name)" in stub
    assert "TODO" in stub or "REWRITE" in stub
    assert "end" in stub


def test_lua_entity_properties():
    """Test LuaEntity properties."""
    from swesmith.constants import CodeEntity
    
    # LuaEntity should be a subclass of CodeEntity
    assert issubclass(LuaEntity, CodeEntity)
    
    # LuaEntity should have required properties
    assert hasattr(LuaEntity, 'name')
    assert hasattr(LuaEntity, 'signature')
    assert hasattr(LuaEntity, 'stub')

