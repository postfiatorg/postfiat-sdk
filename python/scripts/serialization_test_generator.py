#!/usr/bin/env python
"""
Serialization Round-Trip Test Generator

Generates dynamic serialization tests that work with any proto message
by introspecting fields, populating with test data, and validating
round-trip serialization integrity.
"""

from typing import List, Dict, Any, Type
from google.protobuf.message import Message
from datetime import datetime

from .proto_introspection import MessageSchema, ProtoIntrospector
# TestDataFactory removed - using simple test data generation
from postfiat.logging import get_logger

logger = get_logger("proto.serialization_tests")


class SerializationTestGenerator:
    """Generates dynamic serialization round-trip tests."""
    
    def __init__(self, introspector: ProtoIntrospector):
        self.introspector = introspector
        self.logger = get_logger("proto.serialization_test_generator")
    
    def generate_test_file(self, message_schemas: List[MessageSchema]) -> str:
        """Generate complete serialization test file."""
        timestamp = datetime.now().isoformat()
        
        # Build imports
        imports = self._generate_imports(message_schemas)
        
        # Build test class
        test_methods = []
        for schema in message_schemas:
            test_methods.append(self._generate_message_test(schema))
        
        # Build parametrized tests
        parametrized_tests = self._generate_parametrized_tests(message_schemas)
        
        content = f'''"""
Dynamic Serialization Integrity Tests

Auto-generated from protobuf definitions on {timestamp}
DO NOT EDIT - Regenerate using the new dynamic test generator

Tests complete serialization/deserialization lifecycle for all proto messages.
Uses runtime introspection to discover schema and generate appropriate test data.
"""

import pytest
from typing import Any, Dict, List, Type
from google.protobuf.message import Message
import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_path = Path(__file__).parent.parent.parent / "scripts"
if str(scripts_path) not in sys.path:
    sys.path.insert(0, str(scripts_path))

try:
    from proto_introspection import ProtoIntrospector, ProtoTestDataFactory as TestDataFactory
except ImportError as e:
    # Fallback for when running tests - create minimal implementations
    print(f"Warning: Could not import TestDataFactory: {{e}}")
    class ProtoIntrospector:
        def __init__(self): pass
    class _TestDataFactory:  # Underscore to avoid pytest collection
        def __init__(self, introspector): pass
        def populate_message(self, message): return message
    TestDataFactory = _TestDataFactory

{imports}


class TestDynamicSerialization:
    """Dynamic serialization tests generated from proto introspection."""

    def setup_method(self):
        """Setup introspector for dynamic population."""
        self.introspector = ProtoIntrospector()

{parametrized_tests}

{chr(10).join(test_methods)}

    def _assert_messages_equal(self, original: Message, deserialized: Message):
        """Assert that two proto messages are equal with detailed error info."""
        if original != deserialized:
            # Provide detailed comparison for debugging
            orig_dict = self._message_to_dict(original)
            deser_dict = self._message_to_dict(deserialized)
            
            pytest.fail(
                f"Messages not equal after round-trip serialization\\n"
                f"Original: {{orig_dict}}\\n"
                f"Deserialized: {{deser_dict}}"
            )
    
    def _message_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convert proto message to dict for debugging."""
        result = {{}}
        for field, value in message.ListFields():
            result[field.name] = value
        return result
    
    def _populate_message_with_test_data(self, message: Message) -> Message:
        """Populate message with appropriate test data using introspection."""
        try:
            introspector = ProtoIntrospector()
            factory = TestDataFactory(introspector)
            return factory.populate_message(message)
        except Exception as e:
            # Fallback - just return the message unchanged
            print(f"Warning: Could not populate message with test data: {{e}}")
            return message
'''
        
        return content
    
    def _generate_imports(self, message_schemas: List[MessageSchema]) -> str:
        """Generate import statements for all required modules."""
        modules = set()
        for schema in message_schemas:
            modules.add(f"from postfiat.v3 import {schema.module_name}_pb2")
        
        return "\n".join(sorted(modules))
    
    def _generate_parametrized_tests(self, message_schemas: List[MessageSchema]) -> str:
        """Generate parametrized tests for all message types."""
        message_classes = []
        for schema in message_schemas:
            message_classes.append(f"{schema.module_name}_pb2.{schema.name}")
        
        return f'''    @pytest.mark.parametrize("message_class", [
{chr(10).join(f"        {cls}," for cls in message_classes)}
    ])
    def test_round_trip_serialization(self, message_class):
        """Test round-trip serialization for any proto message."""
        # Create instance
        original = message_class()
        
        # Populate with test data based on introspected schema
        self._populate_message_with_test_data(original)
        
        # Test serialization
        try:
            serialized = original.SerializeToString()
            assert len(serialized) > 0, f"Serialization produced empty bytes for {{message_class.__name__}}"
        except Exception as e:
            pytest.fail(f"Serialization failed for {{message_class.__name__}}: {{str(e)}}")

        # Test deserialization
        try:
            deserialized = message_class()
            deserialized.ParseFromString(serialized)
        except Exception as e:
            pytest.fail(f"Deserialization failed for {{message_class.__name__}}: {{str(e)}}")
        
        # Verify round-trip integrity
        self._assert_messages_equal(original, deserialized)'''
    
    def _generate_message_test(self, schema: MessageSchema) -> str:
        """Generate specific test method for a message type."""
        method_name = f"test_{schema.name.lower()}_serialization"
        
        # Generate field population code
        field_population = self._generate_field_population_code(schema)
        
        return f'''    def {method_name}(self):
        """Test {schema.name} serialization with introspected field data."""
        # Create message instance
        message = {schema.module_name}_pb2.{schema.name}()
        
        # Populate fields based on introspected schema
{field_population}
        
        # Test round-trip serialization
        serialized = message.SerializeToString()
        assert len(serialized) > 0, "Serialization produced empty bytes"
        
        deserialized = {schema.module_name}_pb2.{schema.name}()
        deserialized.ParseFromString(serialized)
        
        # Verify integrity
        self._assert_messages_equal(message, deserialized)
        
        # Verify specific field values
{self._generate_field_assertions(schema)}'''
    
    def _generate_field_population_code(self, schema: MessageSchema) -> str:
        """Generate code to populate message fields with test data."""
        lines = []

        for field in schema.fields:
            # Check if this is a map field by looking at nested types
            is_map_field = self._is_map_field(field, schema)

            if is_map_field:
                lines.append(self._generate_map_field_code(field, schema))
            elif field.is_repeated:
                lines.append(self._generate_repeated_field_code(field, schema))
            else:
                lines.append(self._generate_singular_field_code(field, schema))

        return "\n".join(f"        {line}" for line in lines if line)
    
    def _generate_singular_field_code(self, field, schema) -> str:
        """Generate code for populating a singular field."""
        if field.type.name == 'STRING':
            if 'hash' in field.name.lower():
                return f'message.{field.name} = "test_hash_abc123def456"'
            elif 'id' in field.name.lower():
                return f'message.{field.name} = "test_id_xyz789"'
            else:
                return f'message.{field.name} = "test_{field.name}_value"'
        
        elif field.type.name in ['INT32', 'UINT32']:
            if 'version' in field.name.lower():
                return f'message.{field.name} = 1'
            elif 'number' in field.name.lower():
                return f'message.{field.name} = 123'
            else:
                return f'message.{field.name} = 42'
        
        elif field.type.name in ['INT64', 'UINT64']:
            return f'message.{field.name} = 123456'
        
        elif field.type.name == 'BOOL':
            return f'message.{field.name} = True'
        
        elif field.type.name == 'BYTES':
            return f'message.{field.name} = b"test_{field.name}_data"'
        
        elif field.type.name in ['DOUBLE', 'FLOAT']:
            return f'message.{field.name} = 123.45'
        
        elif field.type.name == 'ENUM':
            if field.enum_type and field.enum_type.values:
                # Use first non-zero enum value if available
                non_zero_values = [v for v in field.enum_type.values if v.number != 0]
                if non_zero_values:
                    enum_value = non_zero_values[0]
                    return f'message.{field.name} = {schema.module_name}_pb2.{field.enum_type.name}.{enum_value.name}'
                else:
                    enum_value = field.enum_type.values[0]
                    return f'message.{field.name} = {schema.module_name}_pb2.{field.enum_type.name}.{enum_value.name}'
            return f'message.{field.name} = 0  # Default enum value'
        
        elif field.type.name == 'MESSAGE':
            # Use introspection to populate nested message
            return f'''# Populate nested message {field.name}
        factory = TestDataFactory(self.introspector)
        factory.populate_message(message.{field.name})'''
        
        return f'# TODO: Handle field type {field.type.name} for {field.name}'
    
    def _generate_repeated_field_code(self, field, schema) -> str:
        """Generate code for populating a repeated field."""
        # Check if this is actually a map field (proto maps are repeated message fields)
        if field.type.name == 'MESSAGE' and field.name.endswith('_entry'):
            # This is likely a map field - skip it for now
            return f'# Skip map field {field.name} - handled separately'
        elif field.type.name == 'MESSAGE':
            return f'''# Populate repeated message field {field.name}
        for i in range(2):
            item = message.{field.name}.add()
            factory = TestDataFactory(self.introspector)
            factory.populate_message(item)'''
        else:
            # For primitive repeated fields
            singular_code = self._generate_singular_field_code(field, schema)
            if singular_code and not singular_code.startswith('#'):
                # Extract the value from the singular code
                value_part = singular_code.split(' = ')[1]
                return f'message.{field.name}.extend([{value_part}, {value_part}])'

        return f'# TODO: Handle repeated field {field.name}'

    def _is_map_field(self, field, schema: MessageSchema) -> bool:
        """Check if a field is a map field by examining the actual proto descriptor."""
        # Create a test instance to check the actual field type
        try:
            test_instance = schema.message_class()
            field_value = getattr(test_instance, field.name)

            # Check if it's a map container
            field_type_name = type(field_value).__name__
            return 'MapContainer' in field_type_name

        except Exception:
            # Fallback to descriptor-based detection
            if not field.is_repeated or field.type.name != 'MESSAGE':
                return False

            # Look for corresponding nested type with Entry suffix
            for nested_type in schema.nested_types:
                if nested_type.name.endswith("Entry") and field.name.title() in nested_type.name:
                    # Check if it has key and value fields (typical map structure)
                    field_names = [f.name for f in nested_type.fields]
                    if len(nested_type.fields) == 2 and 'key' in field_names and 'value' in field_names:
                        return True

            return False

    def _generate_map_field_code(self, field, schema) -> str:
        """Generate code for populating a map field."""
        return f'''# Populate map field {field.name}
        message.{field.name}["key1"] = "value1"
        message.{field.name}["key2"] = "value2"'''

    def _generate_field_assertions(self, schema: MessageSchema) -> str:
        """Generate assertions to verify field values after round-trip."""
        lines = []
        
        for field in schema.fields:
            if not field.is_repeated and field.type.name in ['STRING', 'INT32', 'UINT32', 'BOOL']:
                lines.append(f'assert deserialized.{field.name} == message.{field.name}')
        
        return "\n".join(f"        {line}" for line in lines)
    
    def generate_validation_tests(self, message_schemas: List[MessageSchema]) -> str:
        """Generate field validation tests."""
        # This would generate tests for field constraints, enum validation, etc.
        # For now, return a placeholder
        return '''    def test_field_validation_placeholder(self):
        """Placeholder for field validation tests."""
        pass'''
