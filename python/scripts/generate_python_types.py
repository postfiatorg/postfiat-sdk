#!/usr/bin/env python
"""Generate Python enums and exceptions from protobuf definitions."""

import os
import sys
from pathlib import Path
import importlib.util

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def generate_enums_from_proto():
    """Generate postfiat/types/enums.py from protobuf enums."""

    try:
        # Import protobuf modules directly to avoid package initialization issues
        import sys
        from pathlib import Path
        
        # Add the postfiat/v3 directory to sys.path temporarily
        v3_path = Path(__file__).parent.parent / "postfiat" / "v3"
        sys.path.insert(0, str(v3_path))
        
        try:
            import messages_pb2
            import errors_pb2
        finally:
            # Remove the temporary path
            sys.path.pop(0)
            
    except ImportError as e:
        print(f"Error: Could not import generated protobuf files: {e}")
        print("Make sure to run 'buf generate' first")
        return False

    # Extract enum information from protobuf
    enums_code = '''"""Auto-generated Pydantic-compatible enums from protobuf definitions.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_python_types.py' to regenerate.
"""

from enum import IntEnum
from typing import Union


'''

    # Discover all enum types from all protobuf modules
    enum_types = {}
    protobuf_modules = [
        ('messages_pb2', messages_pb2),
        ('errors_pb2', errors_pb2)
    ]

    # Get all enum descriptors from all protobuf modules
    for module_name, module in protobuf_modules:
        print(f"🔍 Scanning {module_name} for enum types...")
        for name in dir(module):
            if not name.startswith('_'):
                attr = getattr(module, name)
                # Check if this is an enum type (EnumTypeWrapper with DESCRIPTOR)
                if hasattr(attr, 'DESCRIPTOR') and hasattr(attr.DESCRIPTOR, 'values_by_name'):
                    enum_types[name] = attr
                    print(f"📊 Found enum type: {name} in {module_name}")

    if not enum_types:
        print("⚠️  No enum types found in protobuf modules")
        return False

    # Generate enum classes dynamically
    for enum_name, enum_type in enum_types.items():
        # Get all enum values from the descriptor
        enum_values = []
        for value_name, value_descriptor in enum_type.DESCRIPTOR.values_by_name.items():
            enum_values.append((value_name, value_descriptor.number))

        # Sort by value to maintain consistent ordering
        enum_values.sort(key=lambda x: x[1])

        print(f"📝 Generating {enum_name} with {len(enum_values)} values")

        # Generate the enum class
        enums_code += f'class {enum_name}(IntEnum):\n'
        enums_code += f'    """{enum_name} enumeration from protobuf."""\n\n'

        for name, value in enum_values:
            enums_code += f'    {name} = {value}\n'

        enums_code += f'''
    @classmethod
    def from_protobuf(cls, pb_value) -> '{enum_name}':
        """Convert from protobuf enum to Pydantic enum."""
        return cls(int(pb_value))

    def to_protobuf(self):
        """Convert from Pydantic enum to protobuf enum."""
        return int(self)


'''
    
    # Write the generated file
    output_path = Path(__file__).parent.parent / "postfiat" / "types" / "enums.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(enums_code)
    
    print(f"✅ Generated {output_path}")
    return True


def generate_exceptions():
    """Generate postfiat/exceptions.py from protobuf error definitions."""

    try:
        # Import protobuf modules directly to avoid package initialization issues
        import sys
        from pathlib import Path
        
        # Add the postfiat/v3 directory to sys.path temporarily
        v3_path = Path(__file__).parent.parent / "postfiat" / "v3"
        sys.path.insert(0, str(v3_path))
        
        try:
            import errors_pb2
        finally:
            # Remove the temporary path
            sys.path.pop(0)
            
    except ImportError as e:
        print(f"Error: Could not import errors_pb2: {e}")
        print("Make sure to run 'buf generate' first")
        return False

    print("🔍 Generating exceptions from protobuf error definitions...")

    # Start building the exceptions code
    exceptions_code = '''"""Auto-generated PostFiat SDK exceptions from protobuf definitions.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_python_types.py' to regenerate.
"""

from typing import Optional, Any, Dict, Union
from enum import IntEnum


'''

    # Generate ErrorCode, ErrorCategory, and ErrorSeverity enums
    error_enums = ['ErrorCode', 'ErrorCategory', 'ErrorSeverity']
    for enum_name in error_enums:
        if hasattr(errors_pb2, enum_name):
            enum_type = getattr(errors_pb2, enum_name)
            enum_values = []
            for value_name, value_descriptor in enum_type.DESCRIPTOR.values_by_name.items():
                enum_values.append((value_name, value_descriptor.number))

            # Sort by value
            enum_values.sort(key=lambda x: x[1])

            exceptions_code += f'class {enum_name}(IntEnum):\n'
            exceptions_code += f'    """{enum_name} from protobuf error definitions."""\n\n'

            for name, value in enum_values:
                exceptions_code += f'    {name} = {value}\n'

            exceptions_code += '\n\n'

    # Generate base exception classes
    exceptions_code += '''class PostFiatError(Exception):
    """Base exception for all PostFiat SDK errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[Union[int, 'ErrorCode']] = None,
        category: Optional[Union[int, 'ErrorCategory']] = None,
        severity: Optional[Union[int, 'ErrorSeverity']] = None,
        details: Optional[Dict[str, Any]] = None,
        field: Optional[str] = None,
        error_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = ErrorCode(error_code) if error_code is not None else None
        self.category = ErrorCategory(category) if category is not None else None
        self.severity = ErrorSeverity(severity) if severity is not None else ErrorSeverity.ERROR
        self.details = details or {}
        self.field = field
        self.error_id = error_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        from postfiat.logging import get_logger
        logger = get_logger("exceptions.serialization")

        result = {
            'message': self.message,
            'error_code': self.error_code.value if self.error_code else None,
            'category': self.category.value if self.category else None,
            'severity': self.severity.value if self.severity else None,
            'details': self.details,
            'field': self.field,
            'error_id': self.error_id
        }

        logger.debug(
            "Serialized exception to dictionary",
            exception_type=self.__class__.__name__,
            error_code=result['error_code'],
            has_details=bool(self.details),
            has_field=bool(self.field),
            has_error_id=bool(self.error_id)
        )

        return result


'''

    # Generate category-specific exception classes
    category_exceptions = {
        'CLIENT': ('ClientError', 'Base exception for client-side errors.'),
        'SERVER': ('ServerError', 'Base exception for server-side errors.'),
        'NETWORK': ('NetworkError', 'Network communication errors.'),
        'AUTH': ('AuthError', 'Authentication and authorization errors.'),
        'VALIDATION': ('ValidationError', 'Data validation errors.'),
        'CONFIGURATION': ('ConfigurationError', 'Configuration or setup errors.'),
        'BUSINESS': ('BusinessError', 'Business logic errors.'),
        'EXTERNAL': ('ExternalError', 'External service errors.')
    }

    for category_name, (class_name, doc) in category_exceptions.items():
        exceptions_code += f'''class {class_name}(PostFiatError):
    """{doc}"""

    def __init__(self, message: str, error_code: Optional[Union[int, 'ErrorCode']] = None, **kwargs):
        super().__init__(
            message=message,
            error_code=error_code,
            category=ErrorCategory.{category_name},
            **kwargs
        )


'''

    # Generate specific exception classes for common error codes
    specific_exceptions = [
        ('AuthenticationError', 'AuthError', 'AUTHENTICATION_FAILED', 'Authentication failed.'),
        ('AuthorizationError', 'AuthError', 'AUTHORIZATION_FAILED', 'Authorization failed.'),
        ('ValidationFailedError', 'ValidationError', 'VALIDATION_FAILED', 'Data validation failed.'),
        ('ResourceNotFoundError', 'ClientError', 'RESOURCE_NOT_FOUND', 'Requested resource not found.'),
        ('InternalServerError', 'ServerError', 'INTERNAL_SERVER_ERROR', 'Internal server error occurred.'),
        ('ServiceUnavailableError', 'ServerError', 'SERVICE_UNAVAILABLE', 'Service temporarily unavailable.'),
        ('RateLimitError', 'ServerError', 'RATE_LIMIT_EXCEEDED', 'Rate limit exceeded.'),
        ('TimeoutError', 'ServerError', 'TIMEOUT', 'Operation timed out.'),
        ('ConnectionError', 'NetworkError', 'CONNECTION_FAILED', 'Network connection failed.'),
    ]

    for class_name, parent_class, error_code, doc in specific_exceptions:
        exceptions_code += f'''class {class_name}({parent_class}):
    """{doc}"""

    def __init__(self, message: str, **kwargs):
        # Remove error_code from kwargs if present to avoid conflicts
        kwargs.pop('error_code', None)
        super().__init__(
            message=message,
            error_code=ErrorCode.{error_code},
            **kwargs
        )


'''

    # Add utility functions with logging
    exceptions_code += '''def create_exception_from_error_code(
    error_code: Union[int, ErrorCode],
    message: str,
    **kwargs
) -> PostFiatError:
    """Create appropriate exception instance based on error code."""
    from postfiat.logging import get_logger
    logger = get_logger("exceptions.factory")

    if isinstance(error_code, int):
        error_code = ErrorCode(error_code)

    # Log exception creation
    logger.info(
        "Creating exception from error code",
        error_code=error_code.name if hasattr(error_code, 'name') else str(error_code),
        error_value=error_code.value if hasattr(error_code, 'value') else error_code,
        message=message,
        has_details=bool(kwargs.get('details')),
        has_field=bool(kwargs.get('field')),
        has_error_id=bool(kwargs.get('error_id'))
    )

    # Map error codes to specific exception classes
    exception_map = {
        ErrorCode.AUTHENTICATION_FAILED: AuthenticationError,
        ErrorCode.AUTHORIZATION_FAILED: AuthorizationError,
        ErrorCode.VALIDATION_FAILED: ValidationFailedError,
        ErrorCode.RESOURCE_NOT_FOUND: ResourceNotFoundError,
        ErrorCode.INTERNAL_SERVER_ERROR: InternalServerError,
        ErrorCode.SERVICE_UNAVAILABLE: ServiceUnavailableError,
        ErrorCode.RATE_LIMIT_EXCEEDED: RateLimitError,
        ErrorCode.TIMEOUT: TimeoutError,
        ErrorCode.CONNECTION_FAILED: ConnectionError,
    }

    exception_class = exception_map.get(error_code, PostFiatError)

    # Log which exception class was selected
    logger.debug(
        "Selected exception class",
        exception_class=exception_class.__name__,
        is_specific_exception=exception_class != PostFiatError
    )

    return exception_class(message, error_code=error_code, **kwargs)


def create_exception_from_error_info(error_info_dict: Dict[str, Any]) -> PostFiatError:
    """Create exception from ErrorInfo protobuf message dictionary."""
    from postfiat.logging import get_logger
    logger = get_logger("exceptions.error_info")

    # Log ErrorInfo processing
    logger.info(
        "Processing ErrorInfo to create exception",
        error_code=error_info_dict.get('code'),
        has_message=bool(error_info_dict.get('message')),
        has_context=bool(error_info_dict.get('context')),
        has_field=bool(error_info_dict.get('field')),
        has_error_id=bool(error_info_dict.get('error_id')),
        severity=error_info_dict.get('severity')
    )

    return create_exception_from_error_code(
        error_code=error_info_dict.get('code'),
        message=error_info_dict.get('message', 'Unknown error'),
        severity=error_info_dict.get('severity'),
        details=error_info_dict.get('context', {}),
        field=error_info_dict.get('field'),
        error_id=error_info_dict.get('error_id')
    )
'''

    # Write the generated file
    output_path = Path(__file__).parent.parent / "postfiat" / "exceptions.py"

    with open(output_path, 'w') as f:
        f.write(exceptions_code)

    print(f"✅ Generated {output_path}")
    return True


def generate_sqlmodel_models():
    """Generate SQLModel database models from protobuf message definitions."""

    try:
        # Import protobuf modules directly to avoid package initialization issues
        import sys
        from pathlib import Path
        
        # Add the postfiat/v3 directory to sys.path temporarily
        v3_path = Path(__file__).parent.parent / "postfiat" / "v3"
        sys.path.insert(0, str(v3_path))
        
        try:
            import messages_pb2
            import errors_pb2
        finally:
            # Remove the temporary path
            sys.path.pop(0)
            
    except ImportError as e:
        print(f"Error: Could not import generated protobuf files: {e}")
        print("Make sure to run 'buf generate' first")
        return False

    print("🔍 Generating SQLModel models from protobuf message definitions...")

    # Start building the models code
    models_code = '''"""Auto-generated SQLModel database models from protobuf definitions.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_python_types.py' to regenerate.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from pydantic import ConfigDict
import json


'''

    # Generate models for each protobuf message type
    protobuf_modules = [
        ('messages_pb2', messages_pb2),
        ('errors_pb2', errors_pb2)
    ]

    # Discover message types
    message_types = {}
    for module_name, module in protobuf_modules:
        print(f"🔍 Scanning {module_name} for message types...")
        for name in dir(module):
            if not name.startswith('_') and not name.endswith('_pb2'):
                attr = getattr(module, name)
                # Check if this is a message type (has DESCRIPTOR)
                if hasattr(attr, 'DESCRIPTOR') and hasattr(attr.DESCRIPTOR, 'fields'):
                    message_types[name] = attr
                    print(f"📊 Found message type: {name} in {module_name}")

    if not message_types:
        print("⚠️  No message types found in protobuf modules")
        return False

    # Generate SQLModel classes for each message type
    for message_name, message_type in message_types.items():
        print(f"📝 Generating SQLModel for {message_name}")

        # Skip certain message types that shouldn't be database tables
        if message_name in ['ExceptionDefinition']:
            continue

        # Generate the SQLModel class
        models_code += f'class {message_name}(SQLModel, table=True):\n'
        models_code += f'    """SQLModel for {message_name} protobuf message."""\n'
        models_code += f'    model_config = ConfigDict(from_attributes=True)\n\n'

        # Add primary key
        models_code += f'    id: Optional[int] = Field(default=None, primary_key=True)\n'

        # Process each field in the message
        for field in message_type.DESCRIPTOR.fields:
            field_name = field.name
            field_type = field.type

            # Map protobuf types to Python types
            if field_type == field.TYPE_STRING:
                python_type = "Optional[str]"
                default_value = "None"
            elif field_type == field.TYPE_INT32 or field_type == field.TYPE_UINT32:
                python_type = "Optional[int]"
                default_value = "None"
            elif field_type == field.TYPE_INT64 or field_type == field.TYPE_UINT64:
                python_type = "Optional[int]"
                default_value = "None"
            elif field_type == field.TYPE_BOOL:
                python_type = "Optional[bool]"
                default_value = "None"
            elif field_type == field.TYPE_BYTES:
                python_type = "Optional[bytes]"
                default_value = "None"
            elif field_type == field.TYPE_ENUM:
                python_type = "Optional[int]"
                default_value = "None"
            elif field_type == field.TYPE_MESSAGE:
                # Handle nested messages as JSON
                python_type = "Optional[str]"
                default_value = "None"
            else:
                python_type = "Optional[str]"
                default_value = "None"

            # Handle reserved field names
            if field_name == "metadata":
                field_name = "message_metadata"  # Rename to avoid SQLModel conflict

            # Handle repeated fields
            if field.label == field.LABEL_REPEATED:
                if field_name == "message_metadata" or "map" in str(field.message_type).lower():
                    # Handle map fields as JSON
                    python_type = "Optional[str]"
                    models_code += f'    {field_name}: {python_type} = Field(default={default_value}, description="JSON-encoded {field_name}")\n'
                else:
                    # Handle repeated fields as JSON arrays
                    python_type = "Optional[str]"
                    models_code += f'    {field_name}: {python_type} = Field(default={default_value}, description="JSON-encoded list of {field_name}")\n'
            else:
                models_code += f'    {field_name}: {python_type} = Field(default={default_value})\n'

        # Add timestamps
        models_code += f'    created_at: datetime = Field(default_factory=datetime.utcnow)\n'
        models_code += f'    updated_at: Optional[datetime] = Field(default=None)\n'

        models_code += '\n'

        # Add helper methods
        models_code += f'    @classmethod\n'
        models_code += f'    def from_protobuf(cls, pb_message) -> "{message_name}":\n'
        models_code += f'        """Create SQLModel instance from protobuf message."""\n'
        models_code += f'        from postfiat.logging import get_logger\n'
        models_code += f'        logger = get_logger("models.{message_name.lower()}")\n\n'
        models_code += f'        data = {{}}\n'

        # Generate field conversion logic
        for field in message_type.DESCRIPTOR.fields:
            proto_field_name = field.name
            model_field_name = "message_metadata" if proto_field_name == "metadata" else proto_field_name

            if field.label == field.LABEL_REPEATED:
                if proto_field_name == "metadata" or "map" in str(field.message_type).lower():
                    models_code += f'        if hasattr(pb_message, "{proto_field_name}"):\n'
                    models_code += f'            data["{model_field_name}"] = json.dumps(dict(pb_message.{proto_field_name}))\n'
                else:
                    models_code += f'        if hasattr(pb_message, "{proto_field_name}"):\n'
                    models_code += f'            data["{model_field_name}"] = json.dumps(list(pb_message.{proto_field_name}))\n'
            else:
                models_code += f'        if hasattr(pb_message, "{proto_field_name}"):\n'
                models_code += f'            data["{model_field_name}"] = pb_message.{proto_field_name}\n'

        models_code += f'\n        logger.debug(\n'
        models_code += f'            "Converting protobuf to SQLModel",\n'
        models_code += f'            message_type="{message_name}",\n'
        models_code += f'            field_count=len(data)\n'
        models_code += f'        )\n\n'
        models_code += f'        return cls(**data)\n\n'

        # Add to_protobuf method
        models_code += f'    def to_protobuf(self):\n'
        models_code += f'        """Convert SQLModel instance to protobuf message."""\n'
        models_code += f'        from postfiat.v3 import messages_pb2, errors_pb2\n'
        models_code += f'        from postfiat.logging import get_logger\n'
        models_code += f'        logger = get_logger("models.{message_name.lower()}")\n\n'

        # Determine which module contains this message
        if hasattr(messages_pb2, message_name):
            models_code += f'        pb_message = messages_pb2.{message_name}()\n'
        else:
            models_code += f'        pb_message = errors_pb2.{message_name}()\n'

        # Generate field conversion logic
        for field in message_type.DESCRIPTOR.fields:
            proto_field_name = field.name
            model_field_name = "message_metadata" if proto_field_name == "metadata" else proto_field_name

            models_code += f'        if self.{model_field_name} is not None:\n'
            if field.label == field.LABEL_REPEATED:
                if proto_field_name == "metadata" or "map" in str(field.message_type).lower():
                    models_code += f'            metadata_dict = json.loads(self.{model_field_name})\n'
                    models_code += f'            pb_message.{proto_field_name}.update(metadata_dict)\n'
                else:
                    models_code += f'            items = json.loads(self.{model_field_name})\n'
                    models_code += f'            pb_message.{proto_field_name}.extend(items)\n'
            else:
                models_code += f'            pb_message.{proto_field_name} = self.{model_field_name}\n'

        models_code += f'\n        logger.debug(\n'
        models_code += f'            "Converting SQLModel to protobuf",\n'
        models_code += f'            message_type="{message_name}",\n'
        models_code += f'            model_id=self.id\n'
        models_code += f'        )\n\n'
        models_code += f'        return pb_message\n\n\n'

    # Add __all__ export at the end
    model_class_names = [name for name in message_types.keys() if name not in ['ExceptionDefinition']]
    models_code += f'\n# Export all generated models\n__all__ = {model_class_names}\n'

    # Write the generated file
    output_path = Path(__file__).parent.parent / "postfiat" / "models" / "generated.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(models_code)

    print(f"✅ Generated {output_path}")
    return True


def generate_init_files():
    """Generate comprehensive __init__.py files for all modules."""
    print("🔍 Generating __init__.py files...")
    
    # Read version from centralized VERSION file
    version_file = Path(__file__).parent.parent.parent / "VERSION"
    version = "0.1.0"  # default fallback
    if version_file.exists():
        with open(version_file, 'r') as f:
            version = f.read().strip()
    else:
        # Fallback: try to read from existing __init__.py
        init_path = Path(__file__).parent.parent / "postfiat" / "__init__.py"
        if init_path.exists():
            with open(init_path, 'r') as f:
                content = f.read()
                import re
                match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
                if match:
                    version = match.group(1)
    
    # Update version in envelope/__init__.py (non-generated file)
    envelope_init_path = Path(__file__).parent.parent / "postfiat" / "envelope" / "__init__.py"
    if envelope_init_path.exists():
        with open(envelope_init_path, 'r') as f:
            envelope_content = f.read()
        
        # Replace version line
        import re
        envelope_content = re.sub(
            r'__version__\s*=\s*["\'][^"\']*["\']',
            f'__version__ = "{version}"',
            envelope_content
        )
        
        with open(envelope_init_path, 'w') as f:
            f.write(envelope_content)
        
        print(f"✅ Updated version in {envelope_init_path} to {version}")
    
    # Generate enhanced postfiat/__init__.py with all imports
    main_init_code = f'''"""PostFiat Wallet SDK - Python SDK for PostFiat Wallet Protocol.

This SDK provides a complete implementation for interacting with PostFiat services,
including wallet management, messaging, and cryptographic operations.

Auto-generated from protobuf definitions.
DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_python_types.py' to regenerate.
"""

__version__ = "{version}"

# Core functionality imports - handle missing modules during generation
try:
    from . import exceptions
except ImportError:
    pass
try:
    from . import types
except ImportError:
    pass
try:
    from . import client
except ImportError:
    pass
try:
    from . import models
except ImportError:
    pass
try:
    from . import v3
except ImportError:
    pass

# Import commonly used exceptions - handle missing modules during generation
try:
    from .exceptions import (
        PostFiatError,
        ClientError,
        ServerError,
        NetworkError,
        AuthError,
        ValidationError,
        AuthenticationError,
        AuthorizationError,
        ResourceNotFoundError,
        InternalServerError,
        ServiceUnavailableError,
        RateLimitError,
        TimeoutError,
        ConnectionError,
        ConfigurationError,
        BusinessError,
        ExternalError,
        ValidationFailedError,
        ErrorCode,
        ErrorCategory,
        ErrorSeverity,
        create_exception_from_error_code,
        create_exception_from_error_info,
    )
except ImportError:
    # exceptions module not available during generation
    pass

# Import commonly used types - handle missing modules during generation
try:
    from .types import (
        MessageType,
        EncryptionMode,
    )
except ImportError:
    # types module not available during generation
    pass

# Import client functionality - handle missing modules during generation
try:
    from .client.base import (
        BaseClient,
        ClientConfig,
    )
except ImportError:
    # client module not available during generation
    pass

# Import all v3 protobuf messages and enums - handle missing modules during generation
try:
    from .v3 import (
        messages_pb2,
        errors_pb2,
    )
except ImportError:
    # v3 module not available during generation
    pass

# Export all for easy access
__all__ = [
    # Version
    "__version__",
    
    # Modules
    "exceptions",
    "types", 
    "client",
    "models",
    "v3",
    
    # Exceptions
    "PostFiatError",
    "ClientError",
    "ServerError", 
    "NetworkError",
    "AuthError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ResourceNotFoundError",
    "InternalServerError",
    "ServiceUnavailableError",
    "RateLimitError",
    "TimeoutError",
    "ConnectionError",
    "ConfigurationError",
    "BusinessError",
    "ExternalError",
    "ValidationFailedError",
    
    # Error enums
    "ErrorCode",
    "ErrorCategory", 
    "ErrorSeverity",
    
    # Exception factories
    "create_exception_from_error_code",
    "create_exception_from_error_info",
    
    # Types
    "MessageType",
    "EncryptionMode",
    
    # Client
    "BaseClient",
    "ClientConfig",
    
    # Protobuf modules
    "messages_pb2",
    "errors_pb2",
]

# Re-export common classes at package level for convenience
# Use try/except to handle cases where protobuf generation might not have created all classes yet
try:
    from .v3.messages_pb2 import Envelope
    __all__.append("Envelope")
except (ImportError, AttributeError):
    pass

try:
    from .v3.messages_pb2 import ContextReference
    __all__.append("ContextReference")
except (ImportError, AttributeError):
    pass

try:
    from .v3.messages_pb2 import PostFiatEnvelopePayload
    __all__.append("PostFiatEnvelopePayload")
except (ImportError, AttributeError):
    pass

try:
    from .v3.errors_pb2 import ErrorInfo
    __all__.append("ErrorInfo")
except (ImportError, AttributeError):
    pass
'''
    
    output_path = Path(__file__).parent.parent / "postfiat" / "__init__.py"
    with open(output_path, 'w') as f:
        f.write(main_init_code)
    print(f"✅ Generated {output_path}")
    
    # Generate types/__init__.py with comprehensive exports
    types_init_code = '''"""PostFiat SDK - Type definitions package.

This package contains auto-generated type definitions from protobuf files.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_python_types.py' to regenerate.
"""

# Import all enum types - handle case where enums.py doesn't exist yet
try:
    from .enums import *
    # Re-export everything from enums
    from .enums import __all__ as _enums_all
    # Build comprehensive __all__ list
    __all__ = []
    if _enums_all:
        __all__.extend(_enums_all)
except ImportError:
    # enums.py doesn't exist yet (during generation)
    __all__ = []
'''
    
    output_path = Path(__file__).parent.parent / "postfiat" / "types" / "__init__.py"
    with open(output_path, 'w') as f:
        f.write(types_init_code)
    print(f"✅ Generated {output_path}")
    
    # Update the enums.py file to include __all__
    enums_path = Path(__file__).parent.parent / "postfiat" / "types" / "enums.py"
    if enums_path.exists():
        with open(enums_path, 'r') as f:
            enums_content = f.read()
        
        # Extract all class names
        import re
        class_names = re.findall(r'^class (\w+)\(IntEnum\):', enums_content, re.MULTILINE)
        
        # Add __all__ at the end if not present
        if '__all__' not in enums_content:
            all_export = f"\n\n# Export all enum types\n__all__ = {class_names}\n"
            enums_content += all_export
            
            with open(enums_path, 'w') as f:
                f.write(enums_content)
            print(f"✅ Updated {enums_path} with __all__ export")
    
    # Generate client/__init__.py
    client_init_code = '''"""PostFiat SDK - Client functionality.

This module provides client classes for interacting with PostFiat services.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_python_types.py' to regenerate.
"""

from .base import BaseClient, ClientConfig

__all__ = [
    "BaseClient",
    "ClientConfig",
]
'''
    
    output_path = Path(__file__).parent.parent / "postfiat" / "client" / "__init__.py"
    with open(output_path, 'w') as f:
        f.write(client_init_code)
    print(f"✅ Generated {output_path}")
    
    # Generate models/__init__.py
    models_init_code = '''"""PostFiat SDK - Database models.

This module contains SQLModel database models generated from protobuf definitions.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_python_types.py' to regenerate.
"""

# Import all generated models
try:
    from .generated import *
    from .generated import __all__ as _generated_all
    __all__ = _generated_all if _generated_all else []
except ImportError:
    # Models not generated yet
    __all__ = []
'''
    
    output_path = Path(__file__).parent.parent / "postfiat" / "models" / "__init__.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(models_init_code)
    print(f"✅ Generated {output_path}")
    
    return True


def main():
    """Generate all Python types from protobuf definitions."""
    print("🔄 Generating Python types from protobuf definitions...")

    success = True
    success &= generate_enums_from_proto()
    success &= generate_exceptions()
    success &= generate_sqlmodel_models()
    success &= generate_init_files()

    if success:
        print("✅ All Python types generated successfully!")
    else:
        print("❌ Some files failed to generate")
        sys.exit(1)


if __name__ == "__main__":
    main()
