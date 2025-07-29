#!/usr/bin/env python
"""
Script to fix generated Solidity code by removing incomplete codec libraries.
"""

import os
import re
import glob

def fix_generated_solidity_files():
    """Fix generated Solidity files by removing incomplete codec libraries."""
    
    # Find all generated Solidity files
    generated_files = glob.glob("src/generated/**/*.sol", recursive=True)
    
    for file_path in generated_files:
        print(f"Processing {file_path}...")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split content into sections
        sections = []
        current_section = []
        in_library = False
        library_braces = 0
        
        lines = content.split('\n')
        
        for line in lines:
            current_section.append(line)
            
            # Check if we're entering a library
            if line.strip().startswith('library ') and 'Codec' in line:
                in_library = True
                library_braces = 0
            
            if in_library:
                library_braces += line.count('{')
                library_braces -= line.count('}')
                
                # Check if library is complete
                if library_braces <= 0:
                    # Check if this library has helper functions
                    section_content = '\n'.join(current_section)
                    has_helper_functions = (
                        'function check_key(' in section_content and 
                        'function decode_field(' in section_content
                    )
                    
                    if not has_helper_functions and 'Codec' in section_content:
                        library_name = line.strip().split()[1].split('(')[0] if line.strip().startswith('library ') else "Unknown"
                        print(f"  Removing incomplete library: {library_name}")
                        # Remove the library section
                        current_section = current_section[:-len(current_section)]
                    else:
                        # Keep the library, add to sections
                        sections.extend(current_section)
                        current_section = []
                    
                    in_library = False
                    library_braces = 0
            elif not in_library and line.strip() == '}' and not current_section[-2].strip().startswith('library '):
                # End of a non-library section
                sections.extend(current_section)
                current_section = []
        
        # Add any remaining content
        if current_section:
            sections.extend(current_section)
        
        # Write the fixed content back
        fixed_content = '\n'.join(sections)
        
        with open(file_path, 'w') as f:
            f.write(fixed_content)
        
        print(f"  Fixed {file_path}")

if __name__ == "__main__":
    fix_generated_solidity_files() 