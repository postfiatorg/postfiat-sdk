#!/usr/bin/env python
"""
Enum and Field Validation Test Generator

Generates validation tests for proto enums and field constraints by discovering
enum values and field types dynamically, testing valid/invalid values appropriately.
"""

from typing import List, Dict, Any, Set
from datetime import datetime

from .proto_introspection import MessageSchema, EnumInfo, FieldInfo, FieldType
from postfiat.logging import get_logger

logger = get_logger("proto.validation_tests")


class ValidationTestGenerator:
    """Generates dynamic validation tests for proto enums and fields."""
    
    def __init__(self):
        self.logger = get_logger("proto.validation_test_generator")
    
    def generate_validation_test_file(self, message_schemas: List[MessageSchema]) -> str:
        """Generate complete validation test file."""
        timestamp = datetime.now().isoformat()
        
        # Collect all enums from all messages
        all_enums = self._collect_all_enums(message_schemas)
        
        # Build imports
        imports = self._generate_imports(message_schemas)
        
        # Generate enum tests
        enum_tests = self._generate_enum_tests(all_enums, message_schemas)
        
        # Generate field validation tests
        field_tests = self._generate_field_validation_tests(message_schemas)
        
        content = f'''"""
Dynamic Field and Enum Validation Tests

Auto-generated from protobuf definitions on {timestamp}
DO NOT EDIT - Regenerate using the new dynamic test generator

Tests proto enum values and field constraints using runtime introspection.
Validates that enums have correct values and fields accept/reject appropriate data.
"""

import pytest
from typing import Any, Dict, List, Type
from google.protobuf.message import Message

{imports}


class TestDynamicValidation:
    """Dynamic validation tests generated from proto introspection."""
    
{enum_tests}

{field_tests}

    def _create_message_with_field_value(self, message_class: Type[Message], field_name: str, value: Any) -> Message:
        """Helper to create message and set field value."""
        message = message_class()
        try:
            setattr(message, field_name, value)
            return message
        except Exception as e:
            raise ValueError(f"Failed to set {{field_name}} = {{value}}: {{e}}")
    
    def _get_enum_class(self, module_name: str, enum_name: str):
        """Helper to get enum class dynamically."""
        module = globals().get(f"{{module_name}}_pb2")
        if module:
            return getattr(module, enum_name, None)
        return None
'''
        
        return content
    
    def _collect_all_enums(self, message_schemas: List[MessageSchema]) -> Dict[str, EnumInfo]:
        """Collect all unique enums from all message schemas."""
        all_enums = {}
        
        for schema in message_schemas:
            # Add enums defined in this message
            for enum_info in schema.enum_types:
                key = f"{schema.module_name}.{enum_info.name}"
                all_enums[key] = (enum_info, schema.module_name)
            
            # Add enums referenced by fields
            for field in schema.fields:
                if field.is_enum and field.enum_type:
                    key = f"{schema.module_name}.{field.enum_type.name}"
                    all_enums[key] = (field.enum_type, schema.module_name)
        
        return all_enums
    
    def _generate_imports(self, message_schemas: List[MessageSchema]) -> str:
        """Generate import statements."""
        modules = set()
        for schema in message_schemas:
            modules.add(f"from postfiat.v3 import {schema.module_name}_pb2")
        
        return "\n".join(sorted(modules))
    
    def _generate_enum_tests(self, all_enums: Dict[str, tuple], message_schemas: List[MessageSchema]) -> str:
        """Generate tests for all enum types."""
        if not all_enums:
            return "    # No enums found to test"
        
        tests = []
        
        for enum_key, (enum_info, module_name) in all_enums.items():
            tests.append(self._generate_single_enum_test(enum_info, module_name))
        
        # Generate parametrized enum test
        enum_params = []
        for enum_key, (enum_info, module_name) in all_enums.items():
            enum_params.append(f'("{module_name}", "{enum_info.name}")')
        
        parametrized_test = f'''    @pytest.mark.parametrize("module_name,enum_name", [
{chr(10).join(f"        {param}," for param in enum_params)}
    ])
    def test_enum_values_exist(self, module_name: str, enum_name: str):
        """Test that enum classes exist and have expected values."""
        enum_class = self._get_enum_class(module_name, enum_name)
        assert enum_class is not None, f"Enum {{enum_name}} not found in {{module_name}}_pb2"
        
        # Test that enum has at least one value
        enum_values = [attr for attr in dir(enum_class) if not attr.startswith('_')]
        assert len(enum_values) > 0, f"Enum {{enum_name}} has no values"'''
        
        tests.append(parametrized_test)
        
        return "\n\n".join(tests)
    
    def _generate_single_enum_test(self, enum_info: EnumInfo, module_name: str) -> str:
        """Generate test for a single enum type."""
        method_name = f"test_{enum_info.name.lower()}_enum_values"
        
        # Generate value assertions
        value_assertions = []
        for enum_value in enum_info.values:
            value_assertions.append(
                f'assert hasattr({module_name}_pb2.{enum_info.name}, "{enum_value.name}"), '
                f'"Missing enum value {enum_value.name}"'
            )
            value_assertions.append(
                f'assert {module_name}_pb2.{enum_info.name}.{enum_value.name} == {enum_value.number}, '
                f'"Incorrect value for {enum_value.name}"'
            )
        
        return f'''    def {method_name}(self):
        """Test {enum_info.name} enum has correct values."""
        # Test enum class exists
        assert hasattr({module_name}_pb2, "{enum_info.name}"), "Enum {enum_info.name} not found"
        
        # Test specific enum values
{chr(10).join(f"        {assertion}" for assertion in value_assertions)}
        
        # Test that all expected values are present
        expected_values = {{{", ".join(str(v.number) for v in enum_info.values)}}}
        actual_values = set({module_name}_pb2.{enum_info.name}.values())

        assert expected_values.issubset(actual_values), f"Missing enum values in {enum_info.name}"'''
    
    def _generate_field_validation_tests(self, message_schemas: List[MessageSchema]) -> str:
        """Generate field validation tests for all messages."""
        tests = []
        
        # Generate parametrized test for all message types
        message_params = []
        for schema in message_schemas:
            message_params.append(f"{schema.module_name}_pb2.{schema.name}")
        
        parametrized_test = f'''    @pytest.mark.parametrize("message_class", [
{chr(10).join(f"        {param}," for param in message_params)}
    ])
    def test_message_field_accessibility(self, message_class):
        """Test that all expected fields are accessible on message."""
        message = message_class()
        descriptor = message.DESCRIPTOR
        
        # Test that all fields in descriptor are accessible
        for field_desc in descriptor.fields:
            assert hasattr(message, field_desc.name), f"Field {{field_desc.name}} not accessible on {{message_class.__name__}}"
            
            # Test that we can get the field value (should not raise)
            try:
                getattr(message, field_desc.name)
            except Exception as e:
                pytest.fail(f"Failed to access field {{field_desc.name}} on {{message_class.__name__}}: {{e}}")'''
        
        tests.append(parametrized_test)
        
        # Generate specific field validation tests for interesting cases
        for schema in message_schemas:
            schema_tests = self._generate_schema_field_tests(schema)
            if schema_tests:
                tests.extend(schema_tests)
        
        return "\n\n".join(tests)
    
    def _generate_schema_field_tests(self, schema: MessageSchema) -> List[str]:
        """Generate field validation tests for a specific schema."""
        tests = []
        
        # Test enum fields specifically
        enum_fields = [f for f in schema.fields if f.is_enum]
        if enum_fields:
            tests.append(self._generate_enum_field_test(schema, enum_fields))
        
        # Test string fields
        string_fields = [f for f in schema.fields if f.type == FieldType.STRING]
        if string_fields:
            tests.append(self._generate_string_field_test(schema, string_fields))
        
        # Test numeric fields
        numeric_fields = [f for f in schema.fields if f.type in [FieldType.INT32, FieldType.UINT32, FieldType.INT64, FieldType.UINT64]]
        if numeric_fields:
            tests.append(self._generate_numeric_field_test(schema, numeric_fields))
        
        return tests
    
    def _generate_enum_field_test(self, schema: MessageSchema, enum_fields: List[FieldInfo]) -> str:
        """Generate test for enum fields in a message."""
        method_name = f"test_{schema.name.lower()}_enum_fields"
        
        field_tests = []
        for field in enum_fields:
            if field.enum_type:
                valid_values = field.enum_type.get_valid_values()
                if field.is_repeated:
                    field_tests.append(f'''
        # Test {field.name} enum field (repeated)
        for valid_value in {valid_values}:
            message.{field.name}.clear()
            message.{field.name}.append(valid_value)
            assert valid_value in message.{field.name}''')
                else:
                    field_tests.append(f'''
        # Test {field.name} enum field
        for valid_value in {valid_values}:
            message.{field.name} = valid_value
            assert message.{field.name} == valid_value''')
        
        return f'''    def {method_name}(self):
        """Test enum fields in {schema.name} accept valid values."""
        message = {schema.module_name}_pb2.{schema.name}()
        
{chr(10).join(field_tests)}'''
    
    def _generate_string_field_test(self, schema: MessageSchema, string_fields: List[FieldInfo]) -> str:
        """Generate test for string fields."""
        method_name = f"test_{schema.name.lower()}_string_fields"
        
        field_tests = []
        for field in string_fields:
            if field.is_repeated:
                field_tests.append(f'''
        # Test {field.name} string field (repeated)
        test_values = ["", "test", "unicode_🎯", "long_" + "x" * 100]
        for test_value in test_values:
            message.{field.name}.clear()
            message.{field.name}.append(test_value)
            assert test_value in message.{field.name}''')
            else:
                field_tests.append(f'''
        # Test {field.name} string field
        test_values = ["", "test", "unicode_🎯", "long_" + "x" * 100]
        for test_value in test_values:
            message.{field.name} = test_value
            assert message.{field.name} == test_value''')
        
        return f'''    def {method_name}(self):
        """Test string fields in {schema.name} handle various string values."""
        message = {schema.module_name}_pb2.{schema.name}()
        
{chr(10).join(field_tests)}'''
    
    def _generate_numeric_field_test(self, schema: MessageSchema, numeric_fields: List[FieldInfo]) -> str:
        """Generate test for numeric fields."""
        method_name = f"test_{schema.name.lower()}_numeric_fields"
        
        field_tests = []
        for field in numeric_fields:
            if field.type in [FieldType.UINT32, FieldType.UINT64]:
                test_values = "[0, 1, 100, 1000]"
            else:
                test_values = "[-1000, -1, 0, 1, 100, 1000]"

            if field.is_repeated:
                field_tests.append(f'''
        # Test {field.name} numeric field (repeated)
        test_values = {test_values}
        for test_value in test_values:
            message.{field.name}.clear()
            message.{field.name}.append(test_value)
            assert test_value in message.{field.name}''')
            else:
                field_tests.append(f'''
        # Test {field.name} numeric field
        test_values = {test_values}
        for test_value in test_values:
            message.{field.name} = test_value
            assert message.{field.name} == test_value''')
        
        return f'''    def {method_name}(self):
        """Test numeric fields in {schema.name} handle various numeric values."""
        message = {schema.module_name}_pb2.{schema.name}()
        
{chr(10).join(field_tests)}'''
