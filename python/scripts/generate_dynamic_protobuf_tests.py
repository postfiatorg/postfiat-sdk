#!/usr/bin/env python
"""
Dynamic Protobuf Test Generator

COMPLETE REWRITE of the broken hardcoded test generator.

This new generator uses runtime introspection to discover proto schemas
and generates appropriate tests dynamically. No more hardcoded field names!

Features:
- Runtime proto schema introspection
- Dynamic test data generation
- Schema-agnostic test generation
- Automatic adaptation to schema changes
- Real validation of proto contracts

Usage:
    python scripts/generate_dynamic_protobuf_tests.py
"""

import os
import sys
from pathlib import Path
from typing import List, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from postfiat.logging import get_logger

# Import our new dynamic components
from scripts.proto_introspection import ProtoIntrospector
from scripts.serialization_test_generator import SerializationTestGenerator
from scripts.validation_test_generator import ValidationTestGenerator
from scripts.service_test_generator import ServiceTestGenerator
from scripts.schema_evolution_test_generator import SchemaEvolutionTestGenerator

logger = get_logger("proto.dynamic_test_generator")


class DynamicProtobufTestGenerator:
    """
    NEW Dynamic Protobuf Test Generator
    
    Replaces the broken hardcoded approach with proper runtime introspection.
    """
    
    def __init__(self, output_base: str = None):
        # Auto-detect the correct output path based on current working directory
        if output_base is None:
            cwd = Path.cwd()
            if cwd.name == "python":
                # Running from python/ directory (likely CI)
                output_base = "tests"
            else:
                # Running from root directory
                output_base = "python/tests"
        
        self.output_base = Path(output_base)
        self.timestamp = datetime.now().isoformat()
        self.logger = get_logger("proto.dynamic_generator")
        
        # Initialize components
        self.introspector = ProtoIntrospector()
        self.serialization_generator = SerializationTestGenerator(self.introspector)
        self.validation_generator = ValidationTestGenerator()
        self.service_generator = ServiceTestGenerator(self.introspector)
        self.evolution_generator = SchemaEvolutionTestGenerator(self.introspector)
        
        # Proto modules to analyze
        self.proto_modules = self._load_proto_modules()
    
    def _load_proto_modules(self) -> List[Any]:
        """Load all available proto modules."""
        modules = []
        
        try:
            from postfiat.v3 import messages_pb2
            modules.append(messages_pb2)
            self.logger.info("Loaded messages_pb2")
        except ImportError as e:
            self.logger.warning(f"Could not load messages_pb2: {e}")
        
        try:
            from postfiat.v3 import errors_pb2
            modules.append(errors_pb2)
            self.logger.info("Loaded errors_pb2")
        except ImportError as e:
            self.logger.warning(f"Could not load errors_pb2: {e}")
        
        # Try to load service modules
        service_modules = [
            'wallet_service_pb2',
            'discord_service_pb2', 
            'knowledge_service_pb2',
            'event_streaming_service_pb2'
        ]
        
        for module_name in service_modules:
            try:
                module = __import__(f'postfiat.v3.{module_name}', fromlist=[module_name])
                modules.append(module)
                self.logger.info(f"Loaded {module_name}")
            except ImportError:
                self.logger.debug(f"Service module {module_name} not available (expected)")
        
        self.logger.info(f"Loaded {len(modules)} proto modules")
        return modules
    
    def generate_all_tests(self):
        """Generate all test files using dynamic introspection."""
        self.logger.info("🚀 Starting dynamic proto test generation")
        
        # Create output directories
        generated_dir = self.output_base / "generated"
        generated_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover proto messages
        message_classes = self.introspector.discover_proto_messages(self.proto_modules)
        self.logger.info(f"Discovered {len(message_classes)} proto message classes")
        
        # Analyze message schemas
        message_schemas = []
        for msg_class in message_classes:
            try:
                schema = self.introspector.analyze_message(msg_class)
                message_schemas.append(schema)
                self.logger.debug(f"Analyzed {schema.name}: {len(schema.fields)} fields")
            except Exception as e:
                self.logger.error(f"Failed to analyze {msg_class}: {e}")
        
        self.logger.info(f"Analyzed {len(message_schemas)} message schemas")
        
        # Discover services
        services = self.service_generator.discover_services(self.proto_modules)
        self.logger.info(f"Discovered {len(services)} gRPC services")
        
        # Generate test files
        self._generate_serialization_tests(message_schemas, generated_dir)
        self._generate_validation_tests(message_schemas, generated_dir)
        self._generate_service_tests(services, generated_dir)
        self._generate_evolution_tests(message_schemas, generated_dir)
        
        self.logger.info("✅ Dynamic proto test generation complete!")
    
    def _generate_serialization_tests(self, message_schemas, output_dir):
        """Generate serialization integrity tests."""
        self.logger.info("Generating serialization tests...")
        
        try:
            test_content = self.serialization_generator.generate_test_file(message_schemas)
            output_file = output_dir / "test_dynamic_serialization.py"
            output_file.write_text(test_content)
            
            self.logger.info(f"✅ Generated serialization tests: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate serialization tests: {e}")
    
    def _generate_validation_tests(self, message_schemas, output_dir):
        """Generate field and enum validation tests."""
        self.logger.info("Generating validation tests...")
        
        try:
            test_content = self.validation_generator.generate_validation_test_file(message_schemas)
            output_file = output_dir / "test_dynamic_validation.py"
            output_file.write_text(test_content)
            
            self.logger.info(f"✅ Generated validation tests: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate validation tests: {e}")
    
    def _generate_service_tests(self, services, output_dir):
        """Generate gRPC service tests."""
        self.logger.info("Generating service tests...")
        
        try:
            test_content = self.service_generator.generate_service_test_file(services)
            output_file = output_dir / "test_dynamic_services.py"
            output_file.write_text(test_content)
            
            self.logger.info(f"✅ Generated service tests: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to generate service tests: {e}")

    def _generate_evolution_tests(self, message_schemas, output_dir):
        """Generate schema evolution tests."""
        self.logger.info("Generating schema evolution tests...")

        try:
            test_content = self.evolution_generator.generate_evolution_test_file(message_schemas)
            output_file = output_dir / "test_dynamic_evolution.py"
            output_file.write_text(test_content)

            self.logger.info(f"✅ Generated evolution tests: {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to generate evolution tests: {e}")

    def _create_readme(self, output_dir):
        """Create README explaining the new dynamic approach."""
        readme_content = f'''# Dynamic Proto Test Generation

Generated on: {self.timestamp}

## 🎯 New Dynamic Approach

This directory contains tests generated by the **NEW** dynamic proto test generator.

### Key Improvements:

1. **Runtime Introspection**: Discovers proto schema at runtime
2. **No Hardcoded Fields**: Uses actual proto field definitions
3. **Schema Evolution**: Adapts automatically when proto schemas change
4. **Type-Aware**: Generates appropriate test data for each field type
5. **Real Validation**: Actually tests proto contract compliance

### Generated Files:

- `test_dynamic_serialization.py` - Round-trip serialization tests
- `test_dynamic_validation.py` - Field and enum validation tests
- `test_dynamic_services.py` - gRPC service method tests
- `test_dynamic_evolution.py` - Schema evolution and compatibility tests

### Running Tests:

```bash
# Run all dynamic tests
python -m pytest tests/generated/test_dynamic_*.py -v

# Run specific test categories
python -m pytest tests/generated/test_dynamic_serialization.py -v
python -m pytest tests/generated/test_dynamic_validation.py -v
python -m pytest tests/generated/test_dynamic_services.py -v
```

### Regenerating Tests:

```bash
python scripts/generate_dynamic_protobuf_tests.py
```

Tests will automatically adapt to any proto schema changes! 🎯
'''
        
        readme_file = output_dir / "README.md"
        readme_file.write_text(readme_content)
        self.logger.info(f"✅ Created README: {readme_file}")


def main():
    """Main entry point for dynamic test generation."""
    
    generator = DynamicProtobufTestGenerator()
    
    try:
        generator.generate_all_tests()
        generator._create_readme(generator.output_base / "generated")
        
        print()
        print("✅ SUCCESS: Dynamic proto test generation complete!")
        print("🎯 Tests now use runtime introspection instead of hardcoded field names")
        print("🚀 Tests will automatically adapt to proto schema changes")
        print()
        print("Run the new tests:")
        print("  python -m pytest tests/generated/test_dynamic_*.py -v")
        
    except Exception as e:
        logger.error(f"Test generation failed: {e}")
        print(f"❌ FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
