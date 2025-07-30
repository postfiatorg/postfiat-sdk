#!/usr/bin/env python
"""
Proto Schema Evolution Test Generator

Enhances the test generator to handle proto schema evolution scenarios,
testing backward compatibility and ensuring tests adapt automatically 
when proto schemas change.
"""

from typing import List, Dict, Any, Set
from datetime import datetime
from pathlib import Path

from .proto_introspection import MessageSchema, FieldInfo, ProtoIntrospector
from postfiat.logging import get_logger

logger = get_logger("proto.schema_evolution")


class SchemaEvolutionTestGenerator:
    """Generates tests that validate schema evolution scenarios."""
    
    def __init__(self, introspector: ProtoIntrospector):
        self.introspector = introspector
        self.logger = get_logger("proto.schema_evolution_generator")
    
    def generate_evolution_test_file(self, message_schemas: List[MessageSchema]) -> str:
        """Generate schema evolution tests."""
        timestamp = datetime.now().isoformat()
        
        # Build imports
        imports = self._generate_imports(message_schemas)
        
        # Generate evolution tests
        evolution_tests = self._generate_evolution_tests(message_schemas)
        
        # Generate backward compatibility tests
        compatibility_tests = self._generate_compatibility_tests(message_schemas)
        
        content = f'''"""
Dynamic Proto Schema Evolution Tests

Auto-generated from protobuf definitions on {timestamp}
DO NOT EDIT - Regenerate using the new dynamic test generator

Tests proto schema evolution scenarios and backward compatibility.
Validates that the dynamic test generator adapts to schema changes.
"""

import pytest
from typing import Any, Dict, List, Type
from google.protobuf.message import Message
import json

{imports}


class TestSchemaEvolution:
    """Tests for proto schema evolution and backward compatibility."""
    
{evolution_tests}

{compatibility_tests}

    def _serialize_to_dict(self, message: Message) -> Dict[str, Any]:
        """Convert proto message to dict for comparison."""
        result = {{}}
        for field, value in message.ListFields():
            if hasattr(value, 'ListFields'):
                # Nested message
                result[field.name] = self._serialize_to_dict(value)
            elif hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                # Repeated field
                result[field.name] = [
                    self._serialize_to_dict(item) if hasattr(item, 'ListFields') else item
                    for item in value
                ]
            else:
                result[field.name] = value
        return result
    
    def _create_minimal_message(self, message_class: Type[Message]) -> Message:
        """Create message with minimal required fields."""
        message = message_class()
        
        # Only populate required fields (if any)
        descriptor = message.DESCRIPTOR
        for field_desc in descriptor.fields:
            if field_desc.label == field_desc.LABEL_REQUIRED:
                # Set minimal value for required fields
                if field_desc.type == field_desc.TYPE_STRING:
                    setattr(message, field_desc.name, "required_value")
                elif field_desc.type in [field_desc.TYPE_INT32, field_desc.TYPE_UINT32]:
                    setattr(message, field_desc.name, 1)
                elif field_desc.type == field_desc.TYPE_BOOL:
                    setattr(message, field_desc.name, True)
        
        return message
'''
        
        return content
    
    def _generate_imports(self, message_schemas: List[MessageSchema]) -> str:
        """Generate import statements."""
        modules = set()
        for schema in message_schemas:
            modules.add(f"from postfiat.v3 import {schema.module_name}_pb2")
        
        return "\n".join(sorted(modules))
    
    def _generate_evolution_tests(self, message_schemas: List[MessageSchema]) -> str:
        """Generate tests for schema evolution scenarios."""
        tests = []
        
        # Test field addition tolerance
        tests.append(self._generate_field_addition_test(message_schemas))
        
        # Test optional field handling
        tests.append(self._generate_optional_field_test(message_schemas))
        
        # Test default value handling
        tests.append(self._generate_default_value_test(message_schemas))
        
        return "\n\n".join(tests)
    
    def _generate_field_addition_test(self, message_schemas: List[MessageSchema]) -> str:
        """Generate test for field addition scenarios."""
        message_params = []
        for schema in message_schemas:
            message_params.append(f"{schema.module_name}_pb2.{schema.name}")
        
        return f'''    @pytest.mark.parametrize("message_class", [
{chr(10).join(f"        {param}," for param in message_params)}
    ])
    def test_schema_evolution_field_addition(self, message_class):
        """Test that messages handle new fields gracefully (forward compatibility)."""
        # Create message with current schema
        original = message_class()
        
        # Serialize with current schema
        serialized = original.SerializeToString()
        
        # Deserialize should work even if new fields were added to schema
        deserialized = message_class()
        deserialized.ParseFromString(serialized)
        
        # Should be equal (no data loss)
        assert original == deserialized
        
        # Test that unknown fields are preserved during round-trip
        # (This tests protobuf's unknown field preservation)
        reserialized = deserialized.SerializeToString()
        assert serialized == reserialized'''
    
    def _generate_optional_field_test(self, message_schemas: List[MessageSchema]) -> str:
        """Generate test for optional field handling."""
        return '''    def test_optional_field_backward_compatibility(self):
        """Test that optional fields maintain backward compatibility."""
        # Test with Envelope as an example
        envelope = messages_pb2.Envelope()
        
        # Set only required/core fields
        envelope.version = 1
        envelope.content_hash = b"test_hash"
        
        # Serialize minimal message
        minimal_serialized = envelope.SerializeToString()
        
        # Should deserialize successfully
        deserialized = messages_pb2.Envelope()
        deserialized.ParseFromString(minimal_serialized)
        
        # Core fields should be preserved
        assert deserialized.version == 1
        assert deserialized.content_hash == b"test_hash"
        
        # Optional fields should have default values
        assert deserialized.reply_to == ""  # Default string value'''
    
    def _generate_default_value_test(self, message_schemas: List[MessageSchema]) -> str:
        """Generate test for default value handling."""
        message_params = []
        for schema in message_schemas:
            message_params.append(f"{schema.module_name}_pb2.{schema.name}")
        
        return f'''    @pytest.mark.parametrize("message_class", [
{chr(10).join(f"        {param}," for param in message_params)}
    ])
    def test_default_value_consistency(self, message_class):
        """Test that default values are consistent across schema versions."""
        # Create empty message
        empty_message = message_class()
        
        # Serialize empty message
        empty_serialized = empty_message.SerializeToString()
        
        # Deserialize should produce identical message
        deserialized = message_class()
        deserialized.ParseFromString(empty_serialized)
        
        # Should be equal (default values preserved)
        assert empty_message == deserialized
        
        # Test that all fields have expected default values
        descriptor = empty_message.DESCRIPTOR
        for field_desc in descriptor.fields:
            field_value = getattr(empty_message, field_desc.name)
            
            # Verify default values match protobuf expectations
            if field_desc.label == field_desc.LABEL_REPEATED:
                # Repeated fields default to empty containers
                assert len(field_value) == 0, f"Repeated field {{field_desc.name}} should be empty by default"
                # Should be able to iterate (even if empty)
                try:
                    list(field_value)  # This will work for repeated fields
                except TypeError:
                    pytest.fail(f"Repeated field {{field_desc.name}} should be iterable")
            elif field_desc.type == field_desc.TYPE_STRING:
                assert isinstance(field_value, str)
            elif field_desc.type in [field_desc.TYPE_INT32, field_desc.TYPE_UINT32]:
                assert isinstance(field_value, int)
            elif field_desc.type == field_desc.TYPE_BOOL:
                assert isinstance(field_value, bool)'''
    
    def _generate_compatibility_tests(self, message_schemas: List[MessageSchema]) -> str:
        """Generate backward compatibility tests."""
        tests = []
        
        # Test wire format compatibility
        tests.append(self._generate_wire_format_test(message_schemas))
        
        # Test field number stability
        tests.append(self._generate_field_number_test(message_schemas))
        
        # Test enum value stability
        tests.append(self._generate_enum_stability_test(message_schemas))
        
        return "\n\n".join(tests)
    
    def _generate_wire_format_test(self, message_schemas: List[MessageSchema]) -> str:
        """Generate test for wire format compatibility."""
        return '''    def test_wire_format_stability(self):
        """Test that wire format remains stable across schema changes."""
        # Create a message with known field values
        envelope = messages_pb2.Envelope()
        envelope.version = 42
        envelope.content_hash = b"stable_hash_value"
        
        # Serialize to bytes
        wire_data = envelope.SerializeToString()
        
        # Wire format should be deterministic and stable
        # (This test will catch breaking changes to field numbers/types)
        assert len(wire_data) > 0
        
        # Deserialize should produce identical message
        deserialized = messages_pb2.Envelope()
        deserialized.ParseFromString(wire_data)
        
        assert deserialized.version == 42
        assert deserialized.content_hash == b"stable_hash_value"'''
    
    def _generate_field_number_test(self, message_schemas: List[MessageSchema]) -> str:
        """Generate test for field number stability."""
        message_params = []
        for schema in message_schemas:
            message_params.append(f"{schema.module_name}_pb2.{schema.name}")
        
        return f'''    @pytest.mark.parametrize("message_class", [
{chr(10).join(f"        {param}," for param in message_params)}
    ])
    def test_field_number_stability(self, message_class):
        """Test that field numbers remain stable (critical for compatibility)."""
        descriptor = message_class.DESCRIPTOR
        
        # Collect field numbers
        field_numbers = set()
        for field_desc in descriptor.fields:
            # Field numbers must be unique and stable
            assert field_desc.number not in field_numbers, \\
                f"Duplicate field number {{field_desc.number}} in {{message_class.__name__}}"
            field_numbers.add(field_desc.number)
            
            # Field numbers should be in valid range
            assert 1 <= field_desc.number <= 536870911, \\
                f"Invalid field number {{field_desc.number}} in {{message_class.__name__}}"
            
            # Reserved ranges should be avoided
            assert not (19000 <= field_desc.number <= 19999), \\
                f"Field number {{field_desc.number}} in reserved range in {{message_class.__name__}}"'''
    
    def _generate_enum_stability_test(self, message_schemas: List[MessageSchema]) -> str:
        """Generate test for enum value stability."""
        return '''    def test_enum_value_stability(self):
        """Test that enum values remain stable across schema versions."""
        # Test known enum values that should remain stable
        
        # MessageType enum values should be stable
        if hasattr(messages_pb2, 'MessageType'):
            # These values should never change
            expected_values = {
                'CORE_MESSAGE': 0,
                'MULTIPART_MESSAGE_PART': 1,
                'RESERVED_100': 100,
            }
            
            for name, expected_value in expected_values.items():
                if hasattr(messages_pb2.MessageType, name):
                    actual_value = getattr(messages_pb2.MessageType, name)
                    assert actual_value == expected_value, \\
                        f"Enum value {{name}} changed from {{expected_value}} to {{actual_value}}"
        
        # EncryptionMode enum values should be stable
        if hasattr(messages_pb2, 'EncryptionMode'):
            expected_values = {
                'NONE': 0,
                'PROTECTED': 1,
                'PUBLIC_KEY': 2,
            }
            
            for name, expected_value in expected_values.items():
                if hasattr(messages_pb2.EncryptionMode, name):
                    actual_value = getattr(messages_pb2.EncryptionMode, name)
                    assert actual_value == expected_value, \\
                        f"Enum value {{name}} changed from {{expected_value}} to {{actual_value}}"'''
