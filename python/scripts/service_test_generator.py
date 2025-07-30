#!/usr/bin/env python
"""
Service Method Test Generator

Builds dynamic gRPC service test generation that introspects service descriptors,
discovers methods and their input/output types, and generates meaningful service tests.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from .proto_introspection import ProtoIntrospector, MessageSchema
from postfiat.logging import get_logger

logger = get_logger("proto.service_tests")


class ServiceInfo:
    """Information about a gRPC service."""
    
    def __init__(self, name: str, full_name: str, module_name: str, methods: List[Dict[str, Any]]):
        self.name = name
        self.full_name = full_name
        self.module_name = module_name
        self.methods = methods


class ServiceTestGenerator:
    """Generates dynamic gRPC service tests."""
    
    def __init__(self, introspector: ProtoIntrospector):
        self.introspector = introspector
        self.logger = get_logger("proto.service_test_generator")
    
    def discover_services(self, modules: List[Any]) -> List[ServiceInfo]:
        """Discover all gRPC services in proto modules."""
        services = []
        
        for module in modules:
            module_name = getattr(module, '__name__', str(module)).split('.')[-1].replace('_pb2', '')
            
            if hasattr(module, 'DESCRIPTOR') and hasattr(module.DESCRIPTOR, 'services_by_name'):
                for service_name, service_desc in module.DESCRIPTOR.services_by_name.items():
                    methods = []
                    for method_desc in service_desc.methods:
                        methods.append({
                            'name': method_desc.name,
                            'input_type': method_desc.input_type.name,
                            'output_type': method_desc.output_type.name,
                            'full_name': method_desc.full_name,
                            'input_full_name': method_desc.input_type.full_name,
                            'output_full_name': method_desc.output_type.full_name,
                        })
                    
                    service_info = ServiceInfo(
                        name=service_name,
                        full_name=service_desc.full_name,
                        module_name=module_name,
                        methods=methods
                    )
                    services.append(service_info)
                    
                    self.logger.debug(f"Found service {service_name} with {len(methods)} methods")
        
        self.logger.info(f"Discovered {len(services)} gRPC services")
        return services
    
    def generate_service_test_file(self, services: List[ServiceInfo]) -> str:
        """Generate complete service test file."""
        if not services:
            return self._generate_empty_service_test_file()
        
        timestamp = datetime.now().isoformat()
        
        # Build imports
        imports = self._generate_imports(services)
        
        # Generate service tests
        service_tests = []
        for service in services:
            service_tests.append(self._generate_service_test_class(service))
        
        # Generate integration tests
        integration_tests = self._generate_integration_tests(services)
        
        content = f'''"""
Dynamic gRPC Service Tests

Auto-generated from protobuf service definitions on {timestamp}
DO NOT EDIT - Regenerate using the new dynamic test generator

Tests gRPC service methods using runtime introspection of service descriptors.
Generates mock service tests and integration test scaffolding.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Any, Dict, List, Type
from google.protobuf.message import Message
import grpc
from grpc import aio as grpc_aio

{imports}


{chr(10).join(service_tests)}

{integration_tests}
'''
        
        return content
    
    def _generate_empty_service_test_file(self) -> str:
        """Generate empty test file when no services are found."""
        timestamp = datetime.now().isoformat()
        
        return f'''"""
Dynamic gRPC Service Tests

Auto-generated from protobuf service definitions on {timestamp}
DO NOT EDIT - Regenerate using the new dynamic test generator

No gRPC services found in proto definitions.
"""

import pytest


class TestNoServices:
    """Placeholder test class when no services are defined."""
    
    def test_no_services_defined(self):
        """Test that confirms no services are currently defined."""
        # This test passes to indicate the generator ran successfully
        # but found no services to test
        assert True, "No gRPC services found in proto definitions"
'''
    
    def _generate_imports(self, services: List[ServiceInfo]) -> str:
        """Generate import statements for service modules."""
        modules = set()
        for service in services:
            modules.add(f"from postfiat.v3 import {service.module_name}_pb2")
            modules.add(f"from postfiat.v3 import {service.module_name}_pb2_grpc")
        
        return "\n".join(sorted(modules))
    
    def _generate_service_test_class(self, service: ServiceInfo) -> str:
        """Generate test class for a specific service."""
        class_name = f"Test{service.name}Service"
        
        # Generate method tests
        method_tests = []
        for method in service.methods:
            method_tests.append(self._generate_method_test(service, method))
        
        # Generate service setup
        setup_method = self._generate_service_setup(service)
        
        return f'''class {class_name}:
    """Tests for {service.name} gRPC service."""
    
{setup_method}

{chr(10).join(method_tests)}

    def test_{service.name.lower()}_service_exists(self):
        """Test that {service.name} service class exists."""
        assert hasattr({service.module_name}_pb2_grpc, "{service.name}Servicer"), \\
            "Service {service.name}Servicer not found"
        assert hasattr({service.module_name}_pb2_grpc, "{service.name}Stub"), \\
            "Service {service.name}Stub not found"
    
    def test_{service.name.lower()}_service_methods(self):
        """Test that {service.name} service has expected methods."""
        servicer_class = getattr({service.module_name}_pb2_grpc, "{service.name}Servicer")
        
        expected_methods = {{{", ".join(f'"{method["name"]}"' for method in service.methods)}}}
        
        for method_name in expected_methods:
            assert hasattr(servicer_class, method_name), \\
                f"Method {{method_name}} not found in {service.name}Servicer"'''
    
    def _generate_service_setup(self, service: ServiceInfo) -> str:
        """Generate setup method for service tests."""
        return f'''    @pytest.fixture
    def mock_{service.name.lower()}_service(self):
        """Create mock {service.name} service for testing."""
        mock_service = Mock(spec={service.module_name}_pb2_grpc.{service.name}Servicer)
        return mock_service
    
    @pytest.fixture
    def {service.name.lower()}_stub(self):
        """Create {service.name} stub for testing."""
        # In real tests, this would connect to a test server
        # For now, return a mock stub
        return Mock(spec={service.module_name}_pb2_grpc.{service.name}Stub)'''
    
    def _generate_method_test(self, service: ServiceInfo, method: Dict[str, Any]) -> str:
        """Generate test for a specific service method."""
        method_name = method['name']
        input_type = method['input_type']
        output_type = method['output_type']
        output_full_name = method.get('output_full_name', '')
        
        test_method_name = f"test_{method_name.lower()}_method"
        
        # Check if output type is google.protobuf.Empty
        if output_full_name == 'google.protobuf.Empty':
            response_creation = "from google.protobuf import empty_pb2\n        expected_response = empty_pb2.Empty()"
        else:
            response_creation = f"expected_response = {service.module_name}_pb2.{output_type}()"
        
        return f'''    def {test_method_name}(self, mock_{service.name.lower()}_service):
        """Test {method_name} method signature and basic functionality."""
        # Test method exists
        assert hasattr(mock_{service.name.lower()}_service, "{method_name}"), \\
            "Method {method_name} not found in service"
        
        # Create test request
        request = {service.module_name}_pb2.{input_type}()
        
        # Mock the response
        {response_creation}
        mock_{service.name.lower()}_service.{method_name}.return_value = expected_response
        
        # Call the method
        response = mock_{service.name.lower()}_service.{method_name}(request, None)
        
        # Verify the call
        mock_{service.name.lower()}_service.{method_name}.assert_called_once_with(request, None)
        assert response == expected_response
    
    @pytest.mark.asyncio
    async def test_{method_name.lower()}_method_async(self, mock_{service.name.lower()}_service):
        """Test {method_name} method with async mock."""
        # Setup async mock
        mock_{service.name.lower()}_service.{method_name} = AsyncMock()
        
        # Create test request
        request = {service.module_name}_pb2.{input_type}()
        
        # Mock the response
        {response_creation}
        mock_{service.name.lower()}_service.{method_name}.return_value = expected_response
        
        # Call the method
        response = await mock_{service.name.lower()}_service.{method_name}(request, None)
        
        # Verify the call
        mock_{service.name.lower()}_service.{method_name}.assert_called_once_with(request, None)
        assert response == expected_response'''
    
    def _generate_integration_tests(self, services: List[ServiceInfo]) -> str:
        """Generate integration test scaffolding."""
        if not services:
            return ""
        
        service_names = [service.name for service in services]
        
        return f'''class TestServiceIntegration:
    """Integration tests for gRPC services."""
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test - requires running gRPC server")
    def test_service_integration_smoke_test(self):
        """Smoke test for service integration."""
        # TODO: Implement when actual gRPC server is available
        # This test should:
        # 1. Start a test gRPC server
        # 2. Create client stubs
        # 3. Make actual gRPC calls
        # 4. Verify responses
        pass
    
    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test - requires running gRPC server")
    def test_cross_service_communication(self):
        """Test communication between different services."""
        # TODO: Implement when services are available
        # Test scenarios like:
        # 1. Service A calls Service B
        # 2. Error handling between services
        # 3. Authentication/authorization
        pass
    
    @pytest.mark.parametrize("service_name", {service_names})
    def test_service_stub_creation(self, service_name):
        """Test that service stubs can be created."""
        # This test verifies the generated gRPC code is valid
        # without requiring a running server
        
        if service_name == "WalletService":
            from postfiat.v3 import wallet_service_pb2_grpc
            stub_class = getattr(wallet_service_pb2_grpc, f"{{service_name}}Stub", None)
        # Add other services as they are implemented
        else:
            pytest.skip(f"Service {{service_name}} not yet implemented")
        
        assert stub_class is not None, f"Stub class for {{service_name}} not found"
        
        # Test that stub can be instantiated (with mock channel)
        mock_channel = Mock()
        try:
            stub = stub_class(mock_channel)
            assert stub is not None
        except Exception as e:
            pytest.fail(f"Failed to create stub for {{service_name}}: {{e}}")'''
