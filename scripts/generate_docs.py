#!/usr/bin/env python
"""
PostFiat SDK Documentation Generator

Streamlined version that focuses on:
- Protobuf documentation generation  
- API specification copying
- Service matrix generation
- Architecture enum synchronization
- Development enum synchronization (4 sections only)
- Version reference updates

Removed complex filesystem scanning and status checking for static content.
"""

import os
import re
import json
import subprocess
from pathlib import Path
import yaml


def format_auto_generated_section(section_key: str, title: str, content: str) -> str:
    """Format an auto-generated section with consistent structure"""
    return f"""<!-- AUTO-GENERATED SECTION: {section_key} -->

**{title}:**
{content}

<!-- END AUTO-GENERATED SECTION -->"""


def run_command(cmd, cwd=None):
    """Run a shell command and return its output"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        raise


def generate_protobuf_docs():
    """Generate protobuf documentation using buf"""
    print("🔧 Generating protobuf documentation...")
    
    # Change to proto directory
    proto_dir = Path("proto")
    if not proto_dir.exists():
        print("⚠️  Proto directory not found, skipping protobuf docs generation")
        return
    
    try:
        # Run buf generate to create documentation
        cmd = "buf generate --template buf.gen.docs.yaml"
        print(f"Running: {cmd}")
        run_command(cmd, cwd="proto")
        print("✅ Generated protobuf documentation with buf")
    except Exception as e:
        print(f"⚠️  Failed to generate protobuf docs: {e}")
        raise


def copy_api_specs():
    """Copy generated API specifications to docs directory"""
    print("📋 Copying API specifications...")
    
    # Ensure docs/generated/api exists
    api_docs_dir = Path("docs/generated/api")
    api_docs_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy OpenAPI spec if it exists
    openapi_source = Path("api/openapi_v2_generated.swagger.json")
    if openapi_source.exists():
        openapi_dest = api_docs_dir / "openapi_v2_generated.swagger.json"
        import shutil
        shutil.copy2(openapi_source, openapi_dest)
        print(f"  Copied {openapi_source.name}")
    
    # Copy other API specs
    api_source_dir = Path("api")
    if api_source_dir.exists():
        for yaml_file in api_source_dir.glob("*.yaml"):
            yaml_dest = api_docs_dir / yaml_file.name
            import shutil
            shutil.copy2(yaml_file, yaml_dest)
            print(f"  Copied {yaml_file.name}")
    
    # Create OpenAPI markdown wrapper
    openapi_md = Path("docs/api/openapi.md")
    openapi_md.parent.mkdir(parents=True, exist_ok=True)
    
    openapi_content = '''# OpenAPI Specification

This page provides an interactive view of the PostFiat SDK's REST API specification.

<swagger-ui src="/postfiat-sdk/generated/api/openapi_v2_generated.swagger.json"/>
'''
    
    with open(openapi_md, 'w') as f:
        f.write(openapi_content)
    print("  Created api/openapi.md")


def parse_proto_services():
    """Parse protobuf services from messages.proto"""
    proto_file = Path("proto/postfiat/v3/messages.proto")
    if not proto_file.exists():
        print(f"⚠️  Proto file not found: {proto_file}")
        return {}
    
    with open(proto_file, 'r') as f:
        content = f.read()
    
    services = {}
    
    # Find all service definitions
    service_pattern = r'service\s+(\w+)\s*\{([^}]+)\}'
    service_matches = re.findall(service_pattern, content, re.DOTALL)
    
    for service_name, service_content in service_matches:
        if not service_name.startswith('PostFiat'):
            continue
            
        rpcs = []
        
        # Find all RPC definitions within this service
        rpc_pattern = r'rpc\s+(\w+)\s*\(\s*(\w+)\s*\)\s*returns\s*\(\s*(\w+)\s*\)(?:\s*\{([^}]*)\})?'
        rpc_matches = re.findall(rpc_pattern, service_content)
        
        for rpc_name, request_type, response_type, options in rpc_matches:
            rpc_info = {
                'name': rpc_name,
                'request': request_type,
                'response': response_type,
                'http_method': 'POST',  # Default
                'http_path': f'/v3/{rpc_name.lower()}',  # Default
                'auth': True  # Default assume auth required
            }
            
            # Parse HTTP options if present
            if options:
                http_match = re.search(r'option\s+\(google\.api\.http\)\s*=\s*\{([^}]+)\}', options)
                if http_match:
                    http_options = http_match.group(1)
                    
                    # Extract HTTP method and path
                    method_match = re.search(r'(get|post|put|delete|patch)\s*:\s*"([^"]+)"', http_options.lower())
                    if method_match:
                        rpc_info['http_method'] = method_match.group(1).upper()
                        rpc_info['http_path'] = method_match.group(2)
            
            rpcs.append(rpc_info)
        
        if rpcs:
            services[service_name] = rpcs
    
    return services


def generate_openapi_links(http_method, http_path):
    """Generate MkDocs-compatible OpenAPI anchor links"""
    # Convert path to anchor format
    # /v3/agents/{agent_id} -> #delete-v3-agents-agent_id
    anchor_path = http_path.replace('/', '-').replace('{', '').replace('}', '').replace('_', '-')
    if anchor_path.startswith('-'):
        anchor_path = anchor_path[1:]
    
    anchor = f"#{http_method.lower()}-{anchor_path}"
    return f"[{http_method} {http_path}](api/openapi.md{anchor})"


def generate_service_matrix():
    """Generate service matrix tables for SERVICES.md"""
    print("🔧 Generating service matrices...")
    
    services = parse_proto_services()
    matrices = {}
    
    for service_name, rpcs in services.items():
        if not rpcs:
            continue
            
        # Generate table rows
        rows = []
        for rpc in rpcs:
            auth_icon = "🔒 JWT" if rpc['auth'] else "🔓 Public"
            rest_link = generate_openapi_links(rpc['http_method'], rpc['http_path'])
            
            row = f"| {rpc['name']} | {rpc['request']} | {rpc['response']} | {auth_icon} | {rest_link} |"
            rows.append(row)
        
        # Create table
        table_content = """| RPC | Request Message | Response Message | Auth? | REST Path |
|-----|----------------|------------------|-------|-----------|
""" + '\n'.join(rows)
        
        # Map service names to matrix keys
        matrix_key = service_name.lower().replace('postfiat', '').replace('service', '') + '-matrix'
        matrices[matrix_key] = table_content
    
    return matrices


def update_services_documentation():
    """Update SERVICES.md with generated service matrices"""
    print("📝 Updating SERVICES.md with generated content...")
    
    services_file = Path("docs/SERVICES.md")
    if not services_file.exists():
        print(f"⚠️  SERVICES.md not found: {services_file}")
        return
    
    matrices = generate_service_matrix()
    
    # Read current content
    with open(services_file, 'r') as f:
        content = f.read()
    
    # Update each service matrix
    updated_count = 0
    for matrix_key, matrix_content in matrices.items():
        pattern = f'<!-- AUTO-GENERATED SECTION: {matrix_key} -->.*?<!-- END AUTO-GENERATED SECTION -->'
        if re.search(pattern, content, re.DOTALL):
            replacement = f"""<!-- AUTO-GENERATED SECTION: {matrix_key} -->

{matrix_content}

<!-- END AUTO-GENERATED SECTION -->"""
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
            updated_count += 1
    
    # Write back to file
    with open(services_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated SERVICES.md with {updated_count} service matrices")


def parse_proto_enums():
    """Parse enum definitions from protobuf files"""
    proto_file = Path("proto/postfiat/v3/messages.proto")
    if not proto_file.exists():
        return {}
    
    with open(proto_file, 'r') as f:
        content = f.read()
    
    enums = {}
    
    # Find all enum definitions
    enum_pattern = r'enum\s+(\w+)\s*\{([^}]+)\}'
    enum_matches = re.findall(enum_pattern, content, re.DOTALL)
    
    for enum_name, enum_content in enum_matches:
        values = []
        
        # Find all enum values
        value_pattern = r'(\w+)\s*=\s*(\d+);'
        value_matches = re.findall(value_pattern, enum_content)
        
        for value_name, value_number in value_matches:
            values.append((value_name, int(value_number)))
        
        if values:
            enums[enum_name] = values
    
    return enums


def format_enum_for_context(enum_name, enum_values, context):
    """Format enum data for different contexts (protobuf, solidity, python, typescript)"""
    if context == 'protobuf':
        lines = [f"enum {enum_name} {{"]
        for value_name, value_number in enum_values:
            lines.append(f"  {value_name} = {value_number};")
        lines.append("}")
        return '\n'.join(lines)
    
    elif context == 'solidity':
        lines = [f"enum {enum_name} {{"]
        # Solidity enums are 0-indexed by position, not by explicit values
        for i, (value_name, _) in enumerate(enum_values):
            comma = "," if i < len(enum_values) - 1 else ""
            lines.append(f"    {value_name}{comma}")
        lines.append("}")
        return '\n'.join(lines)
    
    elif context == 'python':
        lines = [f"class {enum_name}(IntEnum):"]
        for value_name, value_number in enum_values:
            lines.append(f"    {value_name} = {value_number}")
        return '\n'.join(lines)
    
    elif context == 'typescript':
        lines = [f"export enum {enum_name} {{"]
        for i, (value_name, value_number) in enumerate(enum_values):
            comma = "," if i < len(enum_values) - 1 else ""
            lines.append(f"  {value_name} = {value_number}{comma}")
        lines.append("}")
        return '\n'.join(lines)
    
    return ""


def generate_enum_snippets():
    """Generate enum code snippets for different contexts"""
    enums = parse_proto_enums()
    
    if not enums:
        return {}
    
    # Define which enums to include in which contexts
    enum_configs = {
        'development-python-example': {
            'enum': 'EnvelopeType',
            'context': 'python'
        },
        'development-typescript-example': {
            'enum': 'EnvelopeType', 
            'context': 'typescript'
        },
        'development-solidity-example': {
            'enum': 'EnvelopeType',
            'context': 'solidity'
        },
        'development-solidity-test-example': {
            'enum': 'EnvelopeType',
            'context': 'solidity'
        }
    }
    
    snippets = {}
    
    for snippet_key, config in enum_configs.items():
        enum_name = config['enum']
        context = config['context']
        
        if enum_name in enums:
            snippet_content = format_enum_for_context(enum_name, enums[enum_name], context)
            if snippet_content:
                snippets[snippet_key] = snippet_content
    
    return snippets


def update_architecture_documentation():
    """Update ARCHITECTURE.md with generated enum snippets"""
    print("📝 Updating ARCHITECTURE.md with generated enum snippets...")
    
    architecture_file = Path("docs/ARCHITECTURE.md")
    if not architecture_file.exists():
        print(f"⚠️  ARCHITECTURE.md not found: {architecture_file}")
        return
    
    snippets = generate_enum_snippets()
    
    # Read current content
    with open(architecture_file, 'r') as f:
        content = f.read()
    
    # Update enum snippets
    updated_count = 0
    if snippets:
        for snippet_key, snippet_content in snippets.items():
            if not snippet_key.startswith('architecture-'):
                continue
                
            # Pattern to match the auto-generated section
            pattern = f'<!-- AUTO-GENERATED SECTION: {snippet_key} -->.*?<!-- END AUTO-GENERATED SECTION -->'
            
            # Determine code block language based on section
            if 'python' in snippet_key:
                code_language = 'python'
            elif 'typescript' in snippet_key:
                code_language = 'typescript'  
            elif 'solidity' in snippet_key:
                code_language = 'solidity'
            else:
                code_language = 'protobuf'
            
            replacement = f"""<!-- AUTO-GENERATED SECTION: {snippet_key} -->
```{code_language}
{snippet_content}
```
<!-- END AUTO-GENERATED SECTION -->"""
            
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                updated_count += 1
    
    # Write back to file
    with open(architecture_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated ARCHITECTURE.md with {updated_count} enum snippets")


def update_development_documentation():
    """Update DEVELOPMENT.md with enum snippets only"""
    print("📝 Updating DEVELOPMENT.md with enum snippets...")
    
    development_file = Path("docs/DEVELOPMENT.md")
    if not development_file.exists():
        print(f"⚠️  DEVELOPMENT.md not found: {development_file}")
        return
    
    # Generate enum snippets
    enum_snippets = generate_enum_snippets()
    
    # Read current content
    with open(development_file, 'r') as f:
        content = f.read()
    
    # Update enum snippets only
    updated_count = 0
    if enum_snippets:
        for snippet_key, snippet_content in enum_snippets.items():
            if not snippet_key.startswith('development-'):
                continue
                
            # Pattern to match the auto-generated section
            pattern = f'<!-- AUTO-GENERATED SECTION: {snippet_key} -->.*?<!-- END AUTO-GENERATED SECTION -->'
            
            # Determine code block language based on section
            if 'python' in snippet_key:
                code_language = 'python'
            elif 'typescript' in snippet_key:
                code_language = 'typescript'
            elif 'solidity' in snippet_key:
                code_language = 'solidity'
            else:
                code_language = 'protobuf'
            
            replacement = f"""<!-- AUTO-GENERATED SECTION: {snippet_key} -->
```{code_language}
{snippet_content}
```
<!-- END AUTO-GENERATED SECTION -->"""
            
            if re.search(pattern, content, re.DOTALL):
                content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                updated_count += 1
    
    # Write back to file
    with open(development_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated DEVELOPMENT.md with {updated_count} enum snippets")


def generate_sdk_docs():
    """Generate SDK-specific documentation"""
    print("📚 Generating SDK documentation...")
    
    # Generate Python SDK docs
    python_dir = Path("python")
    if python_dir.exists():
        print("  Generating Python SDK documentation...")
        # You could add sphinx or other doc generation here
    
    # Generate TypeScript SDK docs
    typescript_dir = Path("typescript")
    if typescript_dir.exists():
        print("  Generating TypeScript SDK documentation...")
        # You could add typedoc or other doc generation here


def get_current_version():
    """Get the current version from VERSION file"""
    try:
        with open("VERSION", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("⚠️  VERSION file not found, using fallback version")
        return "0.0.0"


def update_version_references():
    """Update all version references in documentation to match VERSION file"""
    print("🔢 Updating version references...")
    
    current_version = get_current_version()
    print(f"📍 Current version: {current_version}")
    
    # Files to update with their placeholders
    version_updates = [
        "docs/ARCHITECTURE.md",
        "docs/DEVELOPMENT.md", 
        "docs/CONTRIBUTING.md"
    ]
    
    updated_files = []
    
    for file_path_str in version_updates:
        file_path = Path(file_path_str)
        if not file_path.exists():
            print(f"⚠️  {file_path} not found, skipping...")
            continue
            
        try:
            # Read file
            with open(file_path, "r") as f:
                content = f.read()
            
            # Replace version placeholder with current version
            original_content = content
            content = content.replace('{{VERSION}}', current_version)
            
            # Write back if changed
            if content != original_content:
                with open(file_path, "w") as f:
                    f.write(content)
                updated_files.append(str(file_path))
                print(f"✅ Updated version references in {file_path}")
            
        except Exception as e:
            print(f"⚠️  Failed to update {file_path}: {e}")
    
    if updated_files:
        print(f"🔄 Updated {len(updated_files)} files with version {current_version}")
    else:
        print("📋 No version references needed updating")


def main():
    """Main documentation generation function"""
    print("🚀 Generating PostFiat SDK documentation...")
    
    # Change to repository root
    repo_root = Path(__file__).parent.parent
    os.chdir(repo_root)
    
    # Generate all documentation (continue on failures for individual steps)
    try:
        generate_protobuf_docs()
    except Exception as e:
        print(f"⚠️  Protobuf documentation generation failed: {e}")
        print("📋 Continuing with other documentation steps...")
    
    copy_api_specs()
    generate_sdk_docs()
    
    # Generate service documentation with matrices
    try:
        update_services_documentation()
    except Exception as e:
        print(f"⚠️  Service documentation generation failed: {e}")
        print("📋 Continuing with remaining documentation steps...")
    
    # Generate architecture documentation with enum snippets
    try:
        update_architecture_documentation()
    except Exception as e:
        print(f"⚠️  Architecture documentation generation failed: {e}")
        print("📋 Continuing with remaining documentation steps...")
    
    # Generate development documentation with enum snippets
    try:
        update_development_documentation()
    except Exception as e:
        print(f"⚠️  Development documentation generation failed: {e}")
        print("📋 Continuing with remaining documentation steps...")
    
    # Update version references across documentation
    try:
        update_version_references()
    except Exception as e:
        print(f"⚠️  Version reference update failed: {e}")
        print("📋 Continuing with remaining documentation steps...")
    
    print("✅ Documentation generation complete!")
    print("📁 Generated files in docs/generated/")
    print("🌐 Ready for MkDocs build")


if __name__ == "__main__":
    main()