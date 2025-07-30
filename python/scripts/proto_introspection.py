#!/usr/bin/env python
"""
Proto Introspection Engine

Core introspection system for analyzing protobuf message descriptors
and extracting schema information dynamically.

This replaces the hardcoded field name approach with proper runtime
introspection of actual proto definitions.
"""

import inspect
import importlib
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Type, Union
from enum import Enum
from google.protobuf.message import Message
from google.protobuf.descriptor import FieldDescriptor, EnumDescriptor, Descriptor

from postfiat.logging import get_logger

logger = get_logger("proto.introspection")


class FieldType(Enum):
    """Proto field types for type-aware test generation."""
    STRING = FieldDescriptor.TYPE_STRING
    INT32 = FieldDescriptor.TYPE_INT32
    UINT32 = FieldDescriptor.TYPE_UINT32
    INT64 = FieldDescriptor.TYPE_INT64
    UINT64 = FieldDescriptor.TYPE_UINT64
    BOOL = FieldDescriptor.TYPE_BOOL
    BYTES = FieldDescriptor.TYPE_BYTES
    DOUBLE = FieldDescriptor.TYPE_DOUBLE
    FLOAT = FieldDescriptor.TYPE_FLOAT
    ENUM = FieldDescriptor.TYPE_ENUM
    MESSAGE = FieldDescriptor.TYPE_MESSAGE


class FieldLabel(Enum):
    """Proto field labels."""
    OPTIONAL = FieldDescriptor.LABEL_OPTIONAL
    REQUIRED = FieldDescriptor.LABEL_REQUIRED
    REPEATED = FieldDescriptor.LABEL_REPEATED


@dataclass
class EnumValueInfo:
    """Information about a proto enum value."""
    name: str
    number: int


@dataclass
class EnumInfo:
    """Information about a proto enum."""
    name: str
    full_name: str
    values: List[EnumValueInfo]
    
    def get_valid_values(self) -> List[int]:
        """Get list of valid enum values."""
        return [v.number for v in self.values]
    
    def get_default_value(self) -> int:
        """Get default enum value (usually 0)."""
        return self.values[0].number if self.values else 0


@dataclass
class FieldInfo:
    """Information about a proto field."""
    name: str
    number: int
    type: FieldType
    label: FieldLabel
    default_value: Any
    enum_type: Optional[EnumInfo] = None
    message_type: Optional['MessageSchema'] = None
    
    @property
    def is_repeated(self) -> bool:
        """Check if field is repeated."""
        return self.label == FieldLabel.REPEATED
    
    @property
    def is_optional(self) -> bool:
        """Check if field is optional."""
        return self.label == FieldLabel.OPTIONAL
    
    @property
    def is_enum(self) -> bool:
        """Check if field is an enum."""
        return self.type == FieldType.ENUM
    
    @property
    def is_message(self) -> bool:
        """Check if field is a nested message."""
        return self.type == FieldType.MESSAGE


@dataclass
class MessageSchema:
    """Complete schema information for a proto message."""
    name: str
    full_name: str
    module_name: str
    message_class: Type[Message]
    fields: List[FieldInfo]
    nested_types: List['MessageSchema']
    enum_types: List[EnumInfo]
    
    def get_field_by_name(self, name: str) -> Optional[FieldInfo]:
        """Get field info by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None
    
    def get_enum_fields(self) -> List[FieldInfo]:
        """Get all enum fields."""
        return [f for f in self.fields if f.is_enum]
    
    def get_message_fields(self) -> List[FieldInfo]:
        """Get all nested message fields."""
        return [f for f in self.fields if f.is_message]
    
    def get_repeated_fields(self) -> List[FieldInfo]:
        """Get all repeated fields."""
        return [f for f in self.fields if f.is_repeated]


class ProtoIntrospector:
    """Core introspection engine for proto messages."""
    
    def __init__(self):
        self.logger = get_logger("proto.introspector")
        self._message_cache: Dict[str, MessageSchema] = {}
        self._enum_cache: Dict[str, EnumInfo] = {}
    
    def discover_proto_messages(self, modules: List[Any]) -> List[Type[Message]]:
        """Discover all proto message classes in given modules."""
        messages = []
        
        for module in modules:
            module_name = getattr(module, '__name__', str(module))
            self.logger.info(f"Discovering proto messages in {module_name}")
            
            for attr_name in dir(module):
                if attr_name.startswith('_'):
                    continue
                    
                attr = getattr(module, attr_name)
                if self._is_proto_message_class(attr):
                    messages.append(attr)
                    self.logger.debug(f"Found proto message: {attr_name}")
        
        self.logger.info(f"Discovered {len(messages)} proto message classes")
        return messages
    
    def analyze_message(self, message_class: Type[Message]) -> MessageSchema:
        """Analyze a proto message class and extract complete schema."""
        full_name = message_class.DESCRIPTOR.full_name
        
        # Check cache first
        if full_name in self._message_cache:
            return self._message_cache[full_name]
        
        self.logger.debug(f"Analyzing message: {full_name}")
        
        descriptor = message_class.DESCRIPTOR
        module_name = message_class.__module__.split('.')[-1].replace('_pb2', '')
        
        # Analyze fields
        fields = []
        for field_desc in descriptor.fields:
            field_info = self._analyze_field(field_desc)
            fields.append(field_info)
        
        # Analyze nested types
        nested_types = []
        for nested_desc in descriptor.nested_types:
            # Create nested message class
            nested_class = getattr(message_class, nested_desc.name)
            nested_schema = self.analyze_message(nested_class)
            nested_types.append(nested_schema)
        
        # Analyze enum types
        enum_types = []
        for enum_desc in descriptor.enum_types:
            enum_info = self._analyze_enum(enum_desc)
            enum_types.append(enum_info)
        
        schema = MessageSchema(
            name=descriptor.name,
            full_name=full_name,
            module_name=module_name,
            message_class=message_class,
            fields=fields,
            nested_types=nested_types,
            enum_types=enum_types
        )
        
        # Cache the result
        self._message_cache[full_name] = schema
        
        self.logger.debug(f"Analyzed message {full_name}: {len(fields)} fields, "
                         f"{len(nested_types)} nested types, {len(enum_types)} enums")
        
        return schema
    
    def _analyze_field(self, field_desc: FieldDescriptor) -> FieldInfo:
        """Analyze a single proto field."""
        field_type = FieldType(field_desc.type)
        field_label = FieldLabel(field_desc.label)
        
        # Handle enum fields
        enum_type = None
        if field_type == FieldType.ENUM:
            enum_type = self._analyze_enum(field_desc.enum_type)
        
        # Handle message fields (nested types)
        message_type = None
        if field_type == FieldType.MESSAGE:
            try:
                # Try to resolve the message type
                message_type = self._resolve_message_type(field_desc.message_type)
            except Exception as e:
                logger.debug(f"Could not resolve message type for {field_desc.name}: {e}")
                # Leave as None - will be handled gracefully in TestDataFactory
        
        return FieldInfo(
            name=field_desc.name,
            number=field_desc.number,
            type=field_type,
            label=field_label,
            default_value=field_desc.default_value,
            enum_type=enum_type,
            message_type=message_type
        )

    def _resolve_message_type(self, message_desc: Descriptor) -> MessageSchema:
        """Resolve a message type to a MessageSchema."""
        # Try to get the message class
        try:
            # Get the message class from the descriptor
            message_class = self._get_message_class_from_descriptor(message_desc)

            # Create a basic MessageSchema
            return MessageSchema(
                name=message_desc.name,
                full_name=message_desc.full_name,
                module_name=message_desc.file.name,
                message_class=message_class,
                fields=[],  # Don't analyze fields to avoid circular dependencies
                nested_types=[],
                enum_types=[]
            )
        except Exception as e:
            logger.debug(f"Failed to resolve message class for {message_desc.full_name}: {e}")
            raise

    def _get_message_class_from_descriptor(self, message_desc: Descriptor):
        """Get the Python message class from a protobuf descriptor."""
        # Try to find the message class in the current module
        full_name = message_desc.full_name

        # Handle common cases
        if full_name.startswith('postfiat.v3.'):
            # Our own messages
            module_name = 'postfiat.v3.messages_pb2'
            try:
                import importlib
                module = importlib.import_module(module_name)

                # Handle nested classes (e.g., PostFiatA2AMessage.IntegrationMetadataEntry)
                if '.' in full_name.replace('postfiat.v3.', ''):
                    # This is a nested class
                    parts = full_name.replace('postfiat.v3.', '').split('.')
                    parent_class_name = parts[0]
                    nested_class_name = parts[1]
                    parent_class = getattr(module, parent_class_name)
                    return getattr(parent_class, nested_class_name)
                else:
                    # Regular top-level class
                    class_name = message_desc.name
                    return getattr(module, class_name)
            except (ImportError, AttributeError):
                pass
        
        elif full_name.startswith('a2a.v1.'):
            # A2A messages
            module_name = 'a2a.v1.a2a_pb2'
            try:
                import importlib
                module = importlib.import_module(module_name)
                class_name = message_desc.name
                return getattr(module, class_name)
            except (ImportError, AttributeError):
                pass

        # Try to get from the file descriptor's generated module
        try:
            # This is a more general approach
            file_desc = message_desc.file
            if hasattr(file_desc, '_concrete_class'):
                # Try to find the class in the generated module
                module_name = file_desc.package.replace('.', '_') + '_pb2'
                class_name = message_desc.name
                import importlib
                module = importlib.import_module(module_name)
                return getattr(module, class_name)
        except Exception:
            pass

        # If all else fails, raise an exception
        raise ImportError(f"Could not find message class for {full_name}")
    
    def _analyze_enum(self, enum_desc: EnumDescriptor) -> EnumInfo:
        """Analyze a proto enum."""
        full_name = enum_desc.full_name
        
        # Check cache first
        if full_name in self._enum_cache:
            return self._enum_cache[full_name]
        
        values = []
        for value_desc in enum_desc.values:
            values.append(EnumValueInfo(
                name=value_desc.name,
                number=value_desc.number
            ))
        
        enum_info = EnumInfo(
            name=enum_desc.name,
            full_name=full_name,
            values=values
        )
        
        # Cache the result
        self._enum_cache[full_name] = enum_info
        
        return enum_info
    
    def _is_proto_message_class(self, obj: Any) -> bool:
        """Check if object is a proto message class."""
        return (
            inspect.isclass(obj) and
            issubclass(obj, Message) and
            hasattr(obj, 'DESCRIPTOR') and
            hasattr(obj.DESCRIPTOR, 'fields')
        )
    
    def get_field_info(self, message_class: Type[Message], field_name: str) -> Optional[FieldInfo]:
        """Get detailed info about a specific field."""
        schema = self.analyze_message(message_class)
        return schema.get_field_by_name(field_name)
    
    def discover_dependencies(self, message_class: Type[Message]) -> List[Type[Message]]:
        """Find all nested message dependencies."""
        dependencies = []
        schema = self.analyze_message(message_class)
        
        for field in schema.fields:
            if field.is_message and field.message_type:
                dependencies.append(field.message_type.message_class)
                # Recursively find dependencies
                nested_deps = self.discover_dependencies(field.message_type.message_class)
                dependencies.extend(nested_deps)
        
        return list(set(dependencies))  # Remove duplicates


class _ProtoTestDataFactory:
    """Factory for creating test data for protobuf messages using introspection."""

    def __init__(self, introspector: ProtoIntrospector):
        self.introspector = introspector

    def populate_message(self, message: Message) -> Message:
        """Populate a protobuf message with appropriate test data."""
        schema = self.introspector.analyze_message(type(message))

        for field in schema.fields:
            try:
                if field.label == FieldLabel.REPEATED:
                    # For repeated fields, add one test item
                    self._populate_repeated_field(message, field)
                else:
                    # For singular fields, set a test value
                    self._populate_singular_field(message, field)
            except Exception as e:
                logger.debug(f"Failed to populate field {field.name}: {e}")
                continue

        return message

    def _populate_singular_field(self, message: Message, field: FieldInfo):
        """Populate a singular field with test data."""
        if field.type == FieldType.STRING:
            setattr(message, field.name, f"test_{field.name}")
        elif field.type == FieldType.INT32:
            setattr(message, field.name, 42)
        elif field.type == FieldType.UINT32:
            setattr(message, field.name, 42)
        elif field.type == FieldType.INT64:
            setattr(message, field.name, 1234567890)
        elif field.type == FieldType.UINT64:
            setattr(message, field.name, 1234567890)
        elif field.type == FieldType.BOOL:
            setattr(message, field.name, True)
        elif field.type == FieldType.BYTES:
            setattr(message, field.name, b"test_bytes")
        elif field.type == FieldType.DOUBLE:
            setattr(message, field.name, 3.14159)
        elif field.type == FieldType.FLOAT:
            setattr(message, field.name, 2.718)
        elif field.type == FieldType.ENUM and field.enum_type:
            # Set to first non-zero enum value if available
            values = [v.number for v in field.enum_type.values if v.number != 0]
            if values:
                setattr(message, field.name, values[0])
            else:
                setattr(message, field.name, 0)
        elif field.type == FieldType.MESSAGE and field.message_type:
            # Create and populate nested message
            try:
                nested_msg = field.message_type.message_class()
                self.populate_message(nested_msg)
                getattr(message, field.name).CopyFrom(nested_msg)
            except Exception as e:
                logger.debug(f"Failed to create nested message for field {field.name}: {e}")
                # Skip this field if we can't create the nested message

    def _populate_repeated_field(self, message: Message, field: FieldInfo):
        """Populate a repeated field with test data."""
        repeated_field = getattr(message, field.name)

        # Check if this is a map field (has key/value structure)
        if field.message_type and hasattr(field.message_type.message_class.DESCRIPTOR, 'GetOptions'):
            # Check if it's a map entry
            if (hasattr(field.message_type.message_class.DESCRIPTOR, 'GetOptions') and
                field.message_type.message_class.DESCRIPTOR.GetOptions().map_entry):
                # This is a map field - populate it as a map
                self._populate_map_field(message, field)
                return

        if field.type == FieldType.STRING:
            repeated_field.append(f"test_{field.name}_1")
        elif field.type in [FieldType.INT32, FieldType.UINT32]:
            repeated_field.append(42)
        elif field.type in [FieldType.INT64, FieldType.UINT64]:
            repeated_field.append(1234567890)
        elif field.type == FieldType.BOOL:
            repeated_field.append(True)
        elif field.type == FieldType.BYTES:
            repeated_field.append(b"test_bytes")
        elif field.type == FieldType.DOUBLE:
            repeated_field.append(3.14159)
        elif field.type == FieldType.FLOAT:
            repeated_field.append(2.718)
        elif field.type == FieldType.ENUM and field.enum_type:
            # Add first non-zero enum value if available
            values = [v.number for v in field.enum_type.values if v.number != 0]
            if values:
                repeated_field.append(values[0])
            else:
                repeated_field.append(0)
        elif field.type == FieldType.MESSAGE and field.message_type:
            # Create and populate nested message
            try:
                nested_msg = repeated_field.add()
                self.populate_message(nested_msg)
            except Exception as e:
                logger.debug(f"Failed to create nested message for repeated field {field.name}: {e}")
                # Skip this field if we can't create the nested message

    def _populate_map_field(self, message: Message, field: FieldInfo):
        """Populate a map field with test data."""
        map_field = getattr(message, field.name)

        # Add a test entry to the map
        test_key = f"test_key_{field.name}"
        test_value = f"test_value_{field.name}"

        try:
            map_field[test_key] = test_value
        except Exception as e:
            logger.debug(f"Failed to populate map field {field.name}: {e}")
            # Fallback: try to add as a regular repeated field
            try:
                entry = map_field.add()
                if hasattr(entry, 'key'):
                    entry.key = test_key
                if hasattr(entry, 'value'):
                    entry.value = test_value
            except Exception as e2:
                logger.debug(f"Failed to populate map field {field.name} as repeated: {e2}")


# Export alias to avoid pytest collection warnings
ProtoTestDataFactory = _ProtoTestDataFactory
