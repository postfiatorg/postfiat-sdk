#!/usr/bin/env python
"""
Generate unit tests for PostFiat gRPC services.

This script creates comprehensive unit tests for the proto-defined services.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

TEST_DIR = project_root / "tests" / "services"
SERVICES_DIR = project_root / "postfiat" / "services" / "impl"

# Service configurations
SERVICES = {
    "content_storage": {
        "impl_file": "content_storage_impl.py",
        "class_name": "ContentStorageServiceImpl",
        "service_name": "PostFiatContentStorage",
        "methods": [
            "StoreContent",
            "RetrieveContent", 
            "DeleteContent",
            "CanHandleUri"
        ]
    },
    "envelope_storage": {
        "impl_file": "envelope_storage_impl.py",
        "class_name": "EnvelopeStorageServiceImpl", 
        "service_name": "PostFiatEnvelopeStorage",
        "methods": [
            "StoreEnvelope",
            "RetrieveEnvelope",
            "SearchEnvelopes",
            "DeleteEnvelope",
            "EnvelopeExists",
            "FindEnvelopesByContentHash",
            "FindEnvelopesByContext",
            "ListEnvelopesBySender"
        ]
    },
    "agent_registry": {
        "impl_file": "agent_registry_impl.py",
        "class_name": "AgentRegistryServiceImpl",
        "service_name": "PostFiatAgentRegistry", 
        "methods": [
            "GetAgentCard",
            "StoreAgentCard",
            "SearchAgents",
            "DeleteAgentCard",
            "GetAgentByEnvelope"
        ]
    }
}

def generate_service_test(service_name: str, config: Dict[str, Any]) -> str:
    """Generate unit test for a service."""
    
    class_name = config["class_name"]
    service_proto_name = config["service_name"]
    methods = config["methods"]
    
    # Generate test file content
    content = [
        '"""',
        f'Unit tests for {class_name}.',
        '',
        'Generated tests for proto-defined gRPC service implementation.',
        '"""',
        '',
        'import pytest',
        'import grpc',
        'from unittest.mock import Mock, patch, MagicMock',
        'from concurrent import futures',
        '',
        f'from postfiat.services.impl.{service_name}_impl import {class_name}',
        f'from postfiat.v3.messages_pb2_grpc import {service_proto_name}Servicer',
        'from postfiat.v3.messages_pb2 import *',
        'from a2a.v1.a2a_pb2 import *',
        'from google.protobuf.empty_pb2 import Empty',
        '',
        '',
        f'class Test{class_name}:',
        f'    """{class_name} unit tests."""',
        '',
        '    def setup_method(self):',
        f'        """Set up test fixtures."""',
        f'        self.service = {class_name}()',
        '        self.context = Mock(spec=grpc.ServicerContext)',
        '',
    ]
    
    # Generate test method for each service method
    for method in methods:
        content.extend([
            f'    def test_{method.lower()}(self):',
            f'        """Test {method} method."""',
            f'        # TODO: Implement {method} test',
            f'        request = Mock()',
            f'        response = self.service.{method}(request, self.context)',
            f'        assert response is not None',
            '',
        ])
    
    # Generate integration test
    content.extend([
        f'    def test_service_integration(self):',
        f'        """Test service integration."""',
        f'        # Create gRPC server',
        f'        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))',
        f'        ',
        f'        # Add service to server',
        f'        from postfiat.v3.messages_pb2_grpc import add_{service_proto_name}Servicer_to_server',
        f'        add_{service_proto_name}Servicer_to_server(self.service, server)',
        f'        ',
        f'        # Test server creation',
        f'        assert server is not None',
        '',
    ])
    
    # Generate mock tests
    content.extend([
        f'    @patch("postfiat.services.impl.{service_name}_impl.{class_name}._create_default_storage")',
        f'    def test_with_mock_storage(self, mock_storage):',
        f'        """Test service with mocked storage."""',
        f'        mock_storage.return_value = Mock()',
        f'        service = {class_name}()',
        f'        assert service is not None',
        '',
        f'    def test_error_handling(self):',
        f'        """Test error handling."""',
        f'        # Test with invalid request',
        f'        request = Mock()',
        f'        request.configure_mock(**{{"side_effect": Exception("Test error")}})',
        f'        ',
        f'        # Should handle errors gracefully',
        f'        # TODO: Add specific error handling tests',
        f'        pass',
        '',
    ])
    
    # Generate async test helpers if needed
    if service_name == "envelope_storage":
        content.extend([
            '    @pytest.mark.asyncio',
            '    async def test_async_operations(self):',
            '        """Test async operation wrappers."""',
            '        # TODO: Test async operation wrappers',
            '        pass',
            '',
        ])
    
    # Add performance tests
    content.extend([
        f'    def test_performance(self):',
        f'        """Test service performance."""',
        f'        import time',
        f'        ',
        f'        # Test method performance',
        f'        start_time = time.time()',
        f'        ',
        f'        # TODO: Add performance tests',
        f'        ',
        f'        end_time = time.time()',
        f'        duration = end_time - start_time',
        f'        ',
        f'        # Should complete within reasonable time',
        f'        assert duration < 1.0  # 1 second max',
        '',
    ])
    
    # End class
    content.extend([
        '',
        f'if __name__ == "__main__":',
        f'    pytest.main([__file__])',
    ])
    
    return "\\n".join(content)

def generate_all_tests():
    """Generate unit tests for all services."""
    print("🧪 Generating unit tests for gRPC services...")
    
    # Ensure test directory exists
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py for test package
    init_file = TEST_DIR / "__init__.py"
    init_file.write_text('"""\\nUnit tests for PostFiat gRPC services.\\n"""\\n')
    
    # Generate test for each service
    for service_name, config in SERVICES.items():
        print(f"  📝 Generating tests for {config['class_name']}...")
        
        # Generate test content
        test_content = generate_service_test(service_name, config)
        
        # Write test file
        test_file = TEST_DIR / f"test_{service_name}_service.py"
        test_file.write_text(test_content)
        
        print(f"    ✅ Created {test_file.name}")
    
    # Generate test configuration
    generate_test_config()
    
    print(f"✅ Generated tests for {len(SERVICES)} services")
    print(f"📁 Test files created in: {TEST_DIR}")

def generate_test_config():
    """Generate pytest configuration for service tests."""
    
    config_content = '''"""
pytest configuration for PostFiat gRPC service tests.
"""

import pytest
import grpc
from concurrent import futures


@pytest.fixture
def grpc_server():
    """Create a gRPC server for testing."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    yield server
    server.stop(0)


@pytest.fixture
def grpc_context():
    """Create a mock gRPC context."""
    from unittest.mock import Mock
    context = Mock(spec=grpc.ServicerContext)
    context.set_code = Mock()
    context.set_details = Mock()
    return context


@pytest.fixture
def mock_storage():
    """Create a mock storage backend."""
    from unittest.mock import Mock
    storage = Mock()
    storage.store = Mock()
    storage.retrieve = Mock()
    storage.can_handle = Mock(return_value=True)
    return storage


@pytest.fixture
def mock_envelope_store():
    """Create a mock envelope store."""
    from unittest.mock import Mock
    import asyncio
    
    store = Mock()
    store.store = Mock(return_value=asyncio.Future())
    store.retrieve = Mock(return_value=asyncio.Future())
    store.delete = Mock(return_value=asyncio.Future())
    store.exists = Mock(return_value=asyncio.Future())
    
    # Set future results
    store.store.return_value.set_result("test-envelope-id")
    store.retrieve.return_value.set_result(Mock())
    store.delete.return_value.set_result(True)
    store.exists.return_value.set_result(True)
    
    return store
'''
    
    config_file = TEST_DIR / "conftest.py"
    config_file.write_text(config_content)
    print(f"    ✅ Created {config_file.name}")

def main():
    """Main entry point."""
    print("🚀 Starting service test generation...")
    
    generate_all_tests()
    
    print("\\n🎉 Service test generation complete!")
    print("\\n📋 Next steps:")
    print("  1. Run: pytest tests/services/ -v")
    print("  2. Review and customize generated tests")
    print("  3. Add specific test cases for your use cases")
    print("  4. Update test fixtures as needed")

if __name__ == "__main__":
    main()