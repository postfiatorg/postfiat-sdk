#!/usr/bin/env python
"""
Enhanced Protobuf build script for PostFiat Wallet v2.
Generates Python code, Pydantic models, and OpenAPI schemas from .proto files.

This script maintains the .proto files as the single source of truth for:
- Message definitions
- Service definitions  
- API schemas
- Enum definitions
- SDK Manager interfaces
- Client stub implementations

Features:
- Generates Python protobuf classes
- Creates Pydantic-compatible enum classes
- Generates OpenAPI/Swagger specifications
- Creates SDK manager interfaces from services
- Generates client stubs for all services
- Generates Discord bot command mappers
- Validates protobuf consistency
- Provides conversion utilities between protobuf and Pydantic types
"""

import os
import sys
import subprocess
import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Repository root is one level up from python/
repo_root = project_root.parent
PROTO_DIR = repo_root / "proto"
POSTFIAT_PROTO_DIR = PROTO_DIR / "postfiat" / "v3"
MODELS_DIR = project_root / "postfiat" / "models"
MANAGERS_DIR = project_root / "postfiat" / "managers"
SERVICES_DIR = project_root / "postfiat" / "services"
CLIENTS_DIR = project_root / "postfiat" / "clients"
DISCORD_DIR = project_root / "postfiat" / "integrations" / "discord"
API_DIR = repo_root / "api"

@dataclass
class EnumInfo:
    """Information about a protobuf enum for Pydantic generation."""
    name: str
    values: Dict[str, int]
    package: str
    source_file: str
    
@dataclass
class ServiceInfo:
    """Information about a protobuf service for code generation."""
    name: str
    methods: List['MethodInfo']
    package: str
    source_file: str

@dataclass 
class MethodInfo:
    """Information about a service method."""
    name: str
    input_type: str
    output_type: str
    http_method: str
    http_path: str
    description: str

class ProtobufBuilder:
    """Enhanced protobuf builder with comprehensive code generation."""
    
    def __init__(self):
        self.project_root = project_root
        self.repo_root = repo_root
        self.proto_dir = PROTO_DIR
        self.models_dir = MODELS_DIR
        self.managers_dir = MANAGERS_DIR
        self.services_dir = SERVICES_DIR
        self.clients_dir = CLIENTS_DIR
        self.discord_dir = DISCORD_DIR
        self.api_dir = API_DIR
        
        # Ensure directories exist
        for directory in [self.models_dir, self.managers_dir, self.services_dir, 
                         self.clients_dir, self.discord_dir, self.api_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
    def check_dependencies(self) -> bool:
        """Check if required tools are available."""
        required_tools = ["protoc", "buf"]
        missing_tools = []
        
        for tool in required_tools:
            try:
                subprocess.run([tool, "--version"], 
                             capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"❌ Missing required tools: {', '.join(missing_tools)}")
            print("\nInstallation instructions:")
            if "protoc" in missing_tools:
                print("- protoc: https://grpc.io/docs/protoc-installation/")
            if "buf" in missing_tools:
                print("- buf: https://docs.buf.build/installation")
            return False
            
        return True
    
    def find_proto_files(self) -> List[Path]:
        """Find all .proto files in the proto directory."""
        proto_files = list(self.proto_dir.glob("**/*.proto"))
        if not proto_files:
            print(f"❌ No .proto files found in {self.proto_dir}")
            return []
        
        print(f"📁 Found {len(proto_files)} .proto files:")
        for proto_file in proto_files:
            print(f"   {proto_file.relative_to(self.repo_root)}")
        
        return proto_files
    
    def extract_enums_from_proto(self, proto_file: Path) -> List[EnumInfo]:
        """Extract enum definitions from a .proto file."""
        enums = []
        
        try:
            content = proto_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading {proto_file}: {e}")
            return enums
        
        # Extract package name
        package_match = re.search(r'package\s+([^;]+);', content)
        package = package_match.group(1) if package_match else ""
        
        # Find enum blocks
        enum_pattern = r'enum\s+(\w+)\s*\{([^}]+)\}'
        enum_matches = re.finditer(enum_pattern, content, re.MULTILINE | re.DOTALL)
        
        for enum_match in enum_matches:
            enum_name = enum_match.group(1)
            enum_body = enum_match.group(2)
            
            # Extract enum values
            value_pattern = r'(\w+)\s*=\s*(\d+);'
            value_matches = re.finditer(value_pattern, enum_body)
            
            values = {}
            for value_match in value_matches:
                value_name = value_match.group(1)
                value_number = int(value_match.group(2))
                values[value_name] = value_number
            
            if values:
                enums.append(EnumInfo(
                    name=enum_name,
                    values=values,
                    package=package,
                    source_file=proto_file.name
                ))
                
        return enums
    
    def extract_services_from_proto(self, proto_file: Path) -> List[ServiceInfo]:
        """Extract service definitions from a .proto file."""
        services = []
        
        try:
            content = proto_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading {proto_file}: {e}")
            return services
        
        # Extract package name
        package_match = re.search(r'package\s+([^;]+);', content)
        package = package_match.group(1) if package_match else ""
        
        # Find service blocks
        service_pattern = r'service\s+(\w+)\s*\{([^}]+)\}'
        service_matches = re.finditer(service_pattern, content, re.MULTILINE | re.DOTALL)
        
        for service_match in service_matches:
            service_name = service_match.group(1)
            service_body = service_match.group(2)
            
            # Extract RPC methods with details
            methods = self._extract_methods_from_service_body(service_body, content)
            
            if methods:
                services.append(ServiceInfo(
                    name=service_name,
                    methods=methods,
                    package=package,
                    source_file=proto_file.name
                ))
                
        return services
    
    def _extract_methods_from_service_body(self, service_body: str, full_content: str) -> List[MethodInfo]:
        """Extract method information from service body."""
        methods = []
        
        # Find RPC method definitions
        rpc_pattern = r'rpc\s+(\w+)\s*\(([^)]+)\)\s*returns\s*\(([^)]+)\)\s*\{([^}]*)\}'
        rpc_matches = re.finditer(rpc_pattern, service_body, re.MULTILINE | re.DOTALL)
        
        for rpc_match in rpc_matches:
            method_name = rpc_match.group(1)
            input_type = rpc_match.group(2).strip()
            output_type = rpc_match.group(3).strip()
            method_body = rpc_match.group(4)
            
            # Extract HTTP method and path
            http_method = "POST"  # Default
            http_path = f"/v3/{method_name.lower()}"  # Default
            description = f"RPC method {method_name}"  # Default
            
            # Look for HTTP annotations
            http_match = re.search(r'option\s*\(google\.api\.http\)\s*=\s*\{([^}]+)\}', method_body)
            if http_match:
                http_options = http_match.group(1)
                
                # Extract HTTP method
                method_match = re.search(r'(get|post|put|delete|patch):\s*"([^"]+)"', http_options)
                if method_match:
                    http_method = method_match.group(1).upper()
                    http_path = method_match.group(2)
            
            # Look for OpenAPI annotations for description
            openapi_match = re.search(r'summary:\s*"([^"]+)"', method_body)
            if openapi_match:
                description = openapi_match.group(1)
            
            methods.append(MethodInfo(
                name=method_name,
                input_type=input_type,
                output_type=output_type,
                http_method=http_method,
                http_path=http_path,
                description=description
            ))
        
        return methods
    
    def generate_pydantic_enums(self, enums: List[EnumInfo]) -> None:
        """Generate Pydantic-compatible enum classes."""
        if not enums:
            print("ℹ️  No enums found to generate")
            return
        
        print(f"🔧 Generating Pydantic enums for {len(enums)} enums...")
        
        # Group enums by source file (inferred from names)
        enum_groups = {}
        for enum in enums:
            # Determine target file based on enum name patterns
            if "Message" in enum.name or "Encryption" in enum.name:
                target_file = "envelope_enums.py"
            elif "Transaction" in enum.name:
                target_file = "transaction_enums.py"  
            elif "User" in enum.name or "Session" in enum.name:
                target_file = "auth_enums.py"
            elif "Event" in enum.name:
                target_file = "event_enums.py"
            elif "Document" in enum.name or "Knowledge" in enum.name:
                target_file = "knowledge_enums.py"
            elif "Discord" in enum.name or "Natural" in enum.name:
                target_file = "discord_enums.py"
            else:
                target_file = "common_enums.py"
                
            if target_file not in enum_groups:
                enum_groups[target_file] = []
            enum_groups[target_file].append(enum)
        
        # Generate each enum file
        for target_file, file_enums in enum_groups.items():
            self._generate_enum_file(target_file, file_enums)
    
    def _generate_enum_file(self, filename: str, enums: List[EnumInfo]) -> None:
        """Generate a single enum file with multiple enums."""
        file_path = self.models_dir / filename
        
        # Generate file header
        content = ['"""']
        content.append(f"Generated Pydantic-compatible enums from protobuf definitions.")
        content.append("DO NOT EDIT - This file is auto-generated by scripts/build_protobuf.py")
        content.append("")
        content.append("The .proto files are the single source of truth.")
        content.append("To modify enums, update the corresponding .proto file and rebuild.")
        content.append('"""')
        content.append("")
        content.append("from enum import IntEnum")
        content.append("from typing import Union")
        content.append("")
        
        # Import protobuf modules for conversion
        protobuf_imports = set()
        for enum in enums:
            # Only import the module that actually contains the enum
            proto_file = enum.source_file
            if "messages.proto" in proto_file:
                protobuf_imports.add("from .postfiat.v3 import messages_pb2")
            elif "wallet_service.proto" in proto_file:
                protobuf_imports.add("from .postfiat.v3 import wallet_service_pb2")
            elif "discord_service.proto" in proto_file:
                protobuf_imports.add("from .postfiat.v3 import discord_service_pb2")
            elif "event_streaming_service.proto" in proto_file:
                protobuf_imports.add("from .postfiat.v3 import event_streaming_service_pb2")
            elif "knowledge_service.proto" in proto_file:
                protobuf_imports.add("from .postfiat.v3 import knowledge_service_pb2")
        
        content.extend(sorted(protobuf_imports))
        content.append("")
        
        # Generate each enum class
        for i, enum in enumerate(enums):
            if i > 0:
                content.append("")
                content.append("")
            
            # Generate Pydantic enum class
            pydantic_name = f"{enum.name}Enum"
            content.append(f"class {pydantic_name}(IntEnum):")
            content.append(f'    """Pydantic-compatible version of {enum.name} from protobuf."""')
            content.append("")
            
            # Add enum values
            for value_name, value_number in enum.values.items():
                content.append(f"    {value_name} = {value_number}")
            
            content.append("")
            content.append(f"    @classmethod")
            content.append(f"    def from_protobuf(cls, pb_value) -> '{pydantic_name}':")
            content.append(f'        """Convert from protobuf enum to Pydantic enum."""')
            content.append(f"        return cls(int(pb_value))")
            content.append("")
            content.append(f"    def to_protobuf(self):")
            content.append(f'        """Convert from Pydantic enum to protobuf enum."""')
            content.append(f"        return int(self)")
        
        # Generate conversion functions
        content.append("")
        content.append("")
        content.append("# Conversion utility functions")
        
        for enum in enums:
            pydantic_name = f"{enum.name}Enum"
            func_name = enum.name.lower()
            
            content.append("")
            content.append(f"def {func_name}_from_protobuf(pb_value) -> {pydantic_name}:")
            content.append(f'    """Convert protobuf {enum.name} to Pydantic {pydantic_name}."""')
            content.append(f"    return {pydantic_name}.from_protobuf(pb_value)")
            content.append("")
            content.append(f"def {func_name}_to_protobuf(pydantic_value: Union[{pydantic_name}, int]):")
            content.append(f'    """Convert Pydantic {pydantic_name} to protobuf {enum.name}."""')
            content.append(f"    if isinstance(pydantic_value, {pydantic_name}):")
            content.append(f"        return pydantic_value.to_protobuf()")
            content.append(f"    return int(pydantic_value)")
        
        # Write the file
        try:
            file_path.write_text("\n".join(content) + "\n", encoding='utf-8')
            print(f"✅ Generated {filename} with {len(enums)} enums")
        except Exception as e:
            print(f"❌ Error writing {filename}: {e}")
    
    def generate_sdk_managers(self, services: List[ServiceInfo]) -> None:
        """Generate SDK manager classes from service definitions."""
        if not services:
            print("ℹ️  No services found to generate managers")
            return
        
        print(f"🔧 Generating SDK managers for {len(services)} services...")
        
        for service in services:
            self._generate_manager_class(service)
    
    def _generate_manager_class(self, service: ServiceInfo) -> None:
        """Generate a manager class for a service."""
        # Map service names to manager names
        manager_mapping = {
            "WalletService": "wallet_manager.py",
            "DiscordBotService": "discord_manager.py", 
            "EventStreamingService": "event_manager.py",
            "KnowledgeService": "knowledge_manager.py"
        }
        
        filename = manager_mapping.get(service.name, f"{service.name.lower()}_manager.py")
        file_path = self.managers_dir / filename
        
        # Generate manager class
        content = ['"""']
        content.append(f"Generated SDK Manager for {service.name}")
        content.append("DO NOT EDIT - This file is auto-generated by scripts/build_protobuf.py")
        content.append("")
        content.append("The .proto files are the single source of truth.")
        content.append("To modify the interface, update the corresponding .proto file and rebuild.")
        content.append('"""')
        content.append("")
        content.append("from typing import Optional, List, AsyncIterator")
        content.append("from ..models import *")
        content.append("from ..config import SDKConfig")
        content.append("from ..exceptions import SDKError")
        content.append("")
        
        # Generate manager class
        manager_name = service.name.replace("Service", "Manager")
        content.append(f"class {manager_name}:")
        content.append(f'    """Manager for {service.name} operations."""')
        content.append("")
        content.append("    def __init__(self, config: SDKConfig):")
        content.append("        self.config = config")
        content.append("        # TODO: Initialize gRPC client or HTTP client")
        content.append("")
        
        # Generate method stubs
        for method in service.methods:
            content.append(f"    async def {self._snake_case(method.name)}(self, request) -> dict:")
            content.append(f'        """')
            content.append(f'        {method.description}')
            content.append(f'        ')
            content.append(f'        HTTP: {method.http_method} {method.http_path}')
            content.append(f'        Input: {method.input_type}')
            content.append(f'        Output: {method.output_type}')
            content.append(f'        """')
            content.append(f"        # TODO: Implement {method.name}")
            content.append("        raise NotImplementedError")
            content.append("")
        
        # Write the file
        try:
            file_path.write_text("\n".join(content) + "\n", encoding='utf-8')
            print(f"✅ Generated {filename}")
        except Exception as e:
            print(f"❌ Error writing {filename}: {e}")
    
    def generate_client_stubs(self, services: List[ServiceInfo]) -> None:
        """Generate client stub classes for all services."""
        if not services:
            print("ℹ️  No services found to generate client stubs")
            return
        
        print(f"🔧 Generating client stubs for {len(services)} services...")
        
        for service in services:
            self._generate_client_stub(service)
    
    def _generate_client_stub(self, service: ServiceInfo) -> None:
        """Generate a client stub for a service."""
        filename = f"{service.name.lower()}_client.py"
        file_path = self.clients_dir / filename
        
        # Generate client stub
        content = ['"""']
        content.append(f"Generated Client Stub for {service.name}")
        content.append("DO NOT EDIT - This file is auto-generated by scripts/build_protobuf.py")
        content.append("")
        content.append("This client can be used to make HTTP requests to the gRPC-Gateway REST API")
        content.append("or direct gRPC calls to the service.")
        content.append('"""')
        content.append("")
        content.append("import httpx")
        content.append("import grpc")
        content.append("from typing import Optional, Dict, Any, AsyncIterator")
        content.append("from ..models import *")
        content.append("from ..exceptions import ClientError, NetworkError")
        content.append("")
        
        # Generate client class
        client_name = f"{service.name}Client"
        content.append(f"class {client_name}:")
        content.append(f'    """HTTP client for {service.name}."""')
        content.append("")
        content.append("    def __init__(self, base_url: str, api_key: Optional[str] = None):")
        content.append("        self.base_url = base_url.rstrip('/')")
        content.append("        self.api_key = api_key")
        content.append("        self.client = httpx.AsyncClient()")
        content.append("")
        content.append("    async def __aenter__(self):")
        content.append("        return self")
        content.append("")
        content.append("    async def __aexit__(self, exc_type, exc_val, exc_tb):")
        content.append("        await self.client.aclose()")
        content.append("")
        
        # Generate method stubs
        for method in service.methods:
            method_name = self._snake_case(method.name)
            
            content.append(f"    async def {method_name}(self, request: dict) -> dict:")
            content.append(f'        """')
            content.append(f'        {method.description}')
            content.append(f'        ')
            content.append(f'        HTTP: {method.http_method} {method.http_path}')
            content.append(f'        """')
            content.append(f"        url = self.base_url + '{method.http_path}'")
            content.append("        headers = {}")
            content.append("        if self.api_key:")
            content.append("            headers['Authorization'] = f'Bearer {self.api_key}'")
            content.append("")
            
            if method.http_method == "GET":
                content.append("        response = await self.client.get(url, headers=headers, params=request)")
            else:
                content.append(f"        response = await self.client.{method.http_method.lower()}(url, headers=headers, json=request)")
            
            content.append("        response.raise_for_status()")
            content.append("        return response.json()")
            content.append("")
        
        # Write the file
        try:
            file_path.write_text("\n".join(content) + "\n", encoding='utf-8')
            print(f"✅ Generated {filename}")
        except Exception as e:
            print(f"❌ Error writing {filename}: {e}")
    
    def generate_discord_command_mapper(self, services: List[ServiceInfo]) -> None:
        """Generate Discord command mapper from DiscordBotService."""
        discord_service = next((s for s in services if s.name == "DiscordBotService"), None)
        if not discord_service:
            print("ℹ️  No DiscordBotService found, skipping Discord mapper")
            return
        
        print("🔧 Generating Discord command mapper...")
        
        filename = "command_mapper.py"
        file_path = self.discord_dir / filename
        
        content = ['"""']
        content.append("Generated Discord Command Mapper")
        content.append("DO NOT EDIT - This file is auto-generated by scripts/build_protobuf.py")
        content.append("")
        content.append("Maps Discord slash commands to SDK method calls.")
        content.append('"""')
        content.append("")
        content.append("import discord")
        content.append("from discord.ext import commands")
        content.append("from typing import Dict, Callable, Any")
        content.append("from ...managers.discord_manager import DiscordBotManager")
        content.append("")
        
        content.append("class DiscordCommandMapper:")
        content.append('    """Maps Discord commands to SDK manager methods."""')
        content.append("")
        content.append("    def __init__(self, manager: DiscordBotManager):")
        content.append("        self.manager = manager")
        content.append("        self.command_map = self._build_command_map()")
        content.append("")
        content.append("    def _build_command_map(self) -> Dict[str, Callable]:")
        content.append('        """Build mapping of Discord commands to manager methods."""')
        content.append("        return {")
        
        # Generate command mappings
        for method in discord_service.methods:
            if method.name.startswith("Pf") or method.name == "Odv":
                command_name = self._camel_to_snake(method.name).replace("pf_", "")
                if command_name == "odv":
                    command_name = "odv"
                elif not command_name.startswith("pf_"):
                    command_name = f"pf_{command_name}"
                
                content.append(f'            "{command_name}": self.manager.{self._snake_case(method.name)},')
        
        content.append("        }")
        content.append("")
        content.append("    async def execute_command(self, command_name: str, **kwargs) -> dict:")
        content.append('        """Execute a Discord command through the SDK."""')
        content.append("        if command_name not in self.command_map:")
        content.append("            raise ValueError(f'Unknown command: {command_name}')")
        content.append("")
        content.append("        handler = self.command_map[command_name]")
        content.append("        return await handler(kwargs)")
        content.append("")
        content.append("    def get_available_commands(self) -> list:")
        content.append('        """Get list of available Discord commands."""')
        content.append("        return list(self.command_map.keys())")
        
        # Write the file
        try:
            file_path.write_text("\n".join(content) + "\n", encoding='utf-8')
            print(f"✅ Generated Discord command mapper")
        except Exception as e:
            print(f"❌ Error writing Discord command mapper: {e}")
    
    def generate_protobuf_python(self) -> bool:
        """Generate Python protobuf classes using buf."""
        print("🔧 Generating Python protobuf classes...")
        
        try:
            # Change to proto directory for buf commands
            original_dir = os.getcwd()
            os.chdir(self.proto_dir)
            
            # Use buf to generate Python code
            result = subprocess.run([
                "buf", "generate",
                "--template", "buf.gen.yaml"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ buf generate failed:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
            
            print("✅ Generated Python protobuf classes")
            return True
            
        except Exception as e:
            print(f"❌ Error running buf generate: {e}")
            return False
        finally:
            os.chdir(original_dir)
    
    def validate_protobuf_files(self) -> bool:
        """Validate protobuf files using buf lint."""
        print("🔍 Validating protobuf files...")
        
        try:
            original_dir = os.getcwd()
            os.chdir(self.proto_dir)
            
            # Use buf to lint proto files
            result = subprocess.run([
                "buf", "lint"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Protobuf validation failed:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
            
            print("✅ Protobuf files are valid")
            return True
            
        except Exception as e:
            print(f"❌ Error running buf lint: {e}")
            return False
        finally:
            os.chdir(original_dir)
    
    def merge_openapi_specs(self) -> bool:
        """Merge generated OpenAPI spec with existing one."""
        print("🔧 Merging OpenAPI specifications...")
        
        # Check for both possible generated file formats
        generated_yaml = self.api_dir / "openapi_v2_generated.yaml"
        generated_json = self.api_dir / "openapi_v2_generated.swagger.json"
        generated_file = None
        
        if generated_yaml.exists():
            generated_file = generated_yaml
        elif generated_json.exists():
            generated_file = generated_json
        else:
            print(f"⚠️  No generated OpenAPI file found (checked v2 .yaml and .swagger.json)")
            return False
        
        existing_file = self.api_dir / "openapi.yaml"
        backup_file = self.api_dir / "openapi.yaml.bak"
        
        try:
            # Create backup of existing file
            if existing_file.exists():
                existing_file.rename(backup_file)
                print(f"📄 Created backup: {backup_file.name}")
            
            # Load generated OpenAPI spec
            with open(generated_file, 'r', encoding='utf-8') as f:
                if generated_file.suffix == '.json':
                    generated_spec = json.load(f)
                else:
                    generated_spec = yaml.safe_load(f)
            
            # Load existing spec if backup exists
            existing_spec = {}
            if backup_file.exists():
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        existing_spec = yaml.safe_load(f) or {}
                except Exception as e:
                    print(f"⚠️  Could not load existing spec: {e}")
            
            # If we have a Swagger 2.0 generated spec but existing is OpenAPI 3.0,
            # we need to be more careful about merging
            if generated_spec.get('swagger') == '2.0' and existing_spec.get('openapi'):
                print("🔄 Converting Swagger 2.0 to OpenAPI 3.0 during merge...")
                merged_spec = self._merge_swagger2_to_openapi3(existing_spec, generated_spec)
            else:
                # Standard merge for same versions
                merged_spec = self._merge_openapi_specs(existing_spec, generated_spec)
            
            # Write merged specification
            with open(existing_file, 'w', encoding='utf-8') as f:
                yaml.dump(merged_spec, f, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            
            print(f"✅ Merged OpenAPI specifications (from {generated_file.name})")
            return True
            
        except Exception as e:
            print(f"❌ Error merging OpenAPI specs: {e}")
            # Restore backup if merge failed
            if backup_file.exists() and not existing_file.exists():
                backup_file.rename(existing_file)
            return False
    
    def _merge_swagger2_to_openapi3(self, existing_openapi3: dict, generated_swagger2: dict) -> dict:
        """Merge Swagger 2.0 generated spec into existing OpenAPI 3.0 spec."""
        merged = existing_openapi3.copy() if existing_openapi3 else {
            'openapi': '3.0.3',
            'info': {'title': 'PostFiat Wallet API', 'version': '0.1.0'},
            'paths': {},
            'components': {'schemas': {}}
        }
        
        # Convert and merge definitions to components/schemas
        if 'definitions' in generated_swagger2:
            if 'components' not in merged:
                merged['components'] = {}
            if 'schemas' not in merged['components']:
                merged['components']['schemas'] = {}
            
            for schema_name, schema_def in generated_swagger2['definitions'].items():
                # Convert Swagger 2.0 schema to OpenAPI 3.0
                converted_schema = self._convert_swagger2_schema_to_openapi3(schema_def)
                merged['components']['schemas'][schema_name] = converted_schema
        
        # Convert and merge paths (if any)
        if 'paths' in generated_swagger2:
            if 'paths' not in merged:
                merged['paths'] = {}
            
            for path, path_def in generated_swagger2['paths'].items():
                # Convert Swagger 2.0 path to OpenAPI 3.0
                converted_path = self._convert_swagger2_path_to_openapi3(path_def)
                merged['paths'][path] = converted_path
        
        return merged
    
    def _convert_swagger2_schema_to_openapi3(self, swagger2_schema: dict) -> dict:
        """Convert a Swagger 2.0 schema definition to OpenAPI 3.0."""
        # Most schema definitions are compatible, but need to handle some differences
        openapi3_schema = swagger2_schema.copy()
        
        # Handle reference conversions
        if '$ref' in openapi3_schema:
            ref = openapi3_schema['$ref']
            if ref.startswith('#/definitions/'):
                openapi3_schema['$ref'] = ref.replace('#/definitions/', '#/components/schemas/')
        
        # Recursively convert nested schemas
        if 'properties' in openapi3_schema:
            for prop_name, prop_def in openapi3_schema['properties'].items():
                if isinstance(prop_def, dict):
                    openapi3_schema['properties'][prop_name] = self._convert_swagger2_schema_to_openapi3(prop_def)
        
        if 'items' in openapi3_schema and isinstance(openapi3_schema['items'], dict):
            openapi3_schema['items'] = self._convert_swagger2_schema_to_openapi3(openapi3_schema['items'])
        
        return openapi3_schema
    
    def _convert_swagger2_path_to_openapi3(self, swagger2_path: dict) -> dict:
        """Convert a Swagger 2.0 path definition to OpenAPI 3.0."""
        openapi3_path = {}
        
        for method, operation in swagger2_path.items():
            if method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                converted_operation = operation.copy()
                
                # Convert parameters to requestBody for POST/PUT/PATCH
                if 'parameters' in converted_operation and method in ['post', 'put', 'patch']:
                    body_params = [p for p in converted_operation['parameters'] if p.get('in') == 'body']
                    if body_params:
                        # Convert body parameter to requestBody
                        body_param = body_params[0]
                        if 'schema' in body_param:
                            converted_operation['requestBody'] = {
                                'required': body_param.get('required', False),
                                'content': {
                                    'application/json': {
                                        'schema': self._convert_swagger2_schema_to_openapi3(body_param['schema'])
                                    }
                                }
                            }
                        # Remove body parameters from parameters list
                        converted_operation['parameters'] = [
                            p for p in converted_operation['parameters'] if p.get('in') != 'body'
                        ]
                
                # Convert responses
                if 'responses' in converted_operation:
                    for status, response in converted_operation['responses'].items():
                        if 'schema' in response:
                            # Convert to content structure
                            response['content'] = {
                                'application/json': {
                                    'schema': self._convert_swagger2_schema_to_openapi3(response['schema'])
                                }
                            }
                            del response['schema']
                
                openapi3_path[method] = converted_operation
        
        return openapi3_path
    
    def _merge_openapi_specs(self, existing: dict, generated: dict) -> dict:
        """Merge existing and generated OpenAPI specifications."""
        # Start with existing spec structure
        merged = existing.copy() if existing else {}
        
        # Update info section with version consistency
        if 'info' in generated:
            if 'info' not in merged:
                merged['info'] = {}
            
            # Preserve existing info but update version if needed
            merged['info'].update({
                'title': existing.get('info', {}).get('title', 'PostFiat Wallet API'),
                'version': existing.get('info', {}).get('version', '0.1.0'),
                'description': existing.get('info', {}).get('description', 
                                 generated['info'].get('description', ''))
            })
        
        # Merge components/schemas from generated spec
        if 'components' in generated:
            if 'components' not in merged:
                merged['components'] = {}
            
            # Merge schemas, preserving existing ones
            if 'schemas' in generated['components']:
                if 'schemas' not in merged['components']:
                    merged['components']['schemas'] = {}
                
                # Add generated schemas, preferring existing for conflicts
                for schema_name, schema_def in generated['components']['schemas'].items():
                    if schema_name not in merged['components']['schemas']:
                        merged['components']['schemas'][schema_name] = schema_def
        
        # Update paths from generated spec for protobuf-based endpoints
        if 'paths' in generated:
            if 'paths' not in merged:
                merged['paths'] = {}
            
            # Add or update protobuf-generated paths
            for path, path_def in generated['paths'].items():
                # Only update if this is a protobuf-generated endpoint
                if self._is_protobuf_endpoint(path):
                    merged['paths'][path] = path_def
        
        return merged
    
    def _is_protobuf_endpoint(self, path: str) -> bool:
        """Check if an endpoint is generated from protobuf."""
        # Define patterns for protobuf-generated endpoints
        protobuf_patterns = [
            '/v3/',  # Our versioned API
            '/discord/',  # Discord endpoints
            '/events/',   # Event streaming endpoints
            '/knowledge/', # Knowledge endpoints
        ]
        
        return any(pattern in path for pattern in protobuf_patterns)
    
    def _snake_case(self, camel_str: str) -> str:
        """Convert CamelCase to snake_case."""
        # Insert underscores before uppercase letters
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _camel_to_snake(self, camel_str: str) -> str:
        """Convert CamelCase to snake_case."""
        return self._snake_case(camel_str)
    
    def cleanup_generated_files(self) -> None:
        """Clean up temporary generated files."""
        temp_files = [
            self.api_dir / "openapi_generated.yaml",
            self.api_dir / "openapi_generated.json", 
            self.api_dir / "openapi_generated.swagger.json",
            self.api_dir / "openapi_v2_generated.yaml",
            self.api_dir / "openapi_v2_generated.json",
            self.api_dir / "openapi_v2_generated.swagger.json"
        ]
        
        for temp_file in temp_files:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                    print(f"🧹 Cleaned up {temp_file.name}")
                except Exception as e:
                    print(f"⚠️  Could not remove {temp_file}: {e}")
    
    def build(self) -> bool:
        """Run the complete build process."""
        print("🚀 Starting enhanced protobuf build process...")
        print(f"📁 Project root: {self.project_root}")
        print(f"📁 Proto directory: {self.proto_dir}")
        print(f"📁 Models directory: {self.models_dir}")
        print(f"📁 Managers directory: {self.managers_dir}")
        print(f"📁 Services directory: {self.services_dir}")
        print(f"📁 Clients directory: {self.clients_dir}")
        print(f"📁 Discord directory: {self.discord_dir}")
        print(f"📁 API directory: {self.api_dir}")
        print()
        
        # Check dependencies
        if not self.check_dependencies():
            return False
        
        # Find proto files
        proto_files = self.find_proto_files()
        if not proto_files:
            return False
        
        # Validate protobuf files
        if not self.validate_protobuf_files():
            return False
        
        # Generate Python protobuf classes and OpenAPI
        if not self.generate_protobuf_python():
            return False
        
        # Extract and generate enums
        all_enums = []
        all_services = []
        
        for proto_file in proto_files:
            enums = self.extract_enums_from_proto(proto_file)
            services = self.extract_services_from_proto(proto_file)
            all_enums.extend(enums)
            all_services.extend(services)
        
        # Generate Pydantic enums
        if all_enums:
            self.generate_pydantic_enums(all_enums)
        
        # Generate SDK managers from services
        if all_services:
            self.generate_sdk_managers(all_services)
            self.generate_client_stubs(all_services)
            self.generate_discord_command_mapper(all_services)
        
        # Merge OpenAPI specifications
        self.merge_openapi_specs()
        
        # Cleanup temporary files
        self.cleanup_generated_files()
        
        print()
        print("✅ Protobuf build completed successfully!")
        print(f"📄 Generated {len(all_enums)} enum classes")
        print(f"🔌 Found {len(all_services)} services")
        print(f"🎯 Generated {len(all_services)} SDK managers")
        print(f"📡 Generated {len(all_services)} client stubs")
        print(f"🤖 Generated Discord command mapper")
        print(f"📋 Updated OpenAPI specification")
        
        return True

def main():
    """Main entry point."""
    builder = ProtobufBuilder()
    success = builder.build()
    
    if not success:
        print("\n❌ Build failed!")
        sys.exit(1)
    
    print("\n🎉 Build completed successfully!")

if __name__ == "__main__":
    main()