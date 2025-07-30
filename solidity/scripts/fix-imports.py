#!/usr/bin/env python
"""
Fix import statements in generated Solidity files.
The protobuf3-solidity plugin incorrectly places imports inside library blocks.
This script moves them to the top of the file and fixes broken pragma statements.
"""

import os
import re
import glob

def fix_solidity_imports(file_path):
    """Fix import statements in a Solidity file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix broken pragma statements first
    content = re.sub(r'pragma\s+experimental\s+ABIEncoderV2;\s*\n\s*ragma', 'pragma', content)
    content = re.sub(r'pragma solidity[^;]*;\s*\np\s*\n', 'pragma solidity >=0.6.0 <8.0.0;\npragma experimental ABIEncoderV2;\n\n', content)
    
    # Find all import statements
    import_pattern = r'^\s*import\s+["\'][^"\']+["\']\s*;'
    imports = re.findall(import_pattern, content, re.MULTILINE)
    
    if not imports:
        print(f"No imports found in {file_path}")
        return
    
    # Remove all import statements from the content
    content = re.sub(import_pattern, '', content, flags=re.MULTILINE)
    
    # Find the library declaration
    library_match = re.search(r'library\s+(\w+)\s*\{', content)
    if not library_match:
        print(f"Warning: No library found in {file_path}")
        return
    
    # Add imports after the pragma statements and before the library
    pragma_end = content.find('pragma experimental ABIEncoderV2;')
    if pragma_end != -1:
        pragma_end = content.find(';', pragma_end) + 1
        # Insert imports after pragma statements
        import_block = '\n'.join(imports) + '\n\n'
        content = content[:pragma_end] + '\n' + import_block + content[pragma_end:]
    else:
        # Insert at the beginning if no pragma found
        import_block = '\n'.join(imports) + '\n\n'
        content = import_block + content
    
    # Write the fixed content back
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed {len(imports)} imports in {file_path}")

def main():
    """Fix imports in all generated Solidity files."""
    generated_dir = "src/generated"
    
    # Find all .sol files in the generated directory
    sol_files = glob.glob(f"{generated_dir}/**/*.sol", recursive=True)
    
    for file_path in sol_files:
        print(f"Processing {file_path}...")
        fix_solidity_imports(file_path)

if __name__ == "__main__":
    main() 