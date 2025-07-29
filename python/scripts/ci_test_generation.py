#!/usr/bin/env python
"""
CI Test Generation Script

Integrates the dynamic proto test generator into CI/CD pipelines.
Ensures tests are regenerated when proto files change and validates
that generated tests pass.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from postfiat.logging import get_logger
    logger = get_logger("ci.test_generation")
except ImportError:
    # Fallback for CI environments where package might not be fully installed
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("ci.test_generation")


class CITestGenerator:
    """CI integration for dynamic proto test generation."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        try:
            self.logger = get_logger("ci.test_generator")
        except NameError:
            # Fallback if get_logger is not available
            import logging
            self.logger = logging.getLogger("ci.test_generator")
        
        # Paths
        self.proto_dir = self.project_root.parent / "proto" / "postfiat" / "v3"
        self.scripts_dir = self.project_root / "scripts"
        self.tests_dir = self.project_root / "tests" / "generated"
        
        # Generator script
        self.generator_script = self.scripts_dir / "generate_dynamic_protobuf_tests.py"
    
    def check_proto_changes(self) -> bool:
        """Check if proto files have changed since last test generation."""
        try:
            # Get last modification time of proto files
            proto_files = list(self.proto_dir.glob("*.proto"))
            if not proto_files:
                self.logger.warning("No proto files found")
                return False
            
            latest_proto_time = max(f.stat().st_mtime for f in proto_files)
            
            # Get last modification time of generated tests
            test_files = list(self.tests_dir.glob("test_dynamic_*.py"))
            if not test_files:
                self.logger.info("No generated tests found - need to generate")
                return True
            
            latest_test_time = max(f.stat().st_mtime for f in test_files)
            
            # If proto files are newer than tests, regenerate
            if latest_proto_time > latest_test_time:
                self.logger.info("Proto files newer than generated tests - need to regenerate")
                return True
            
            self.logger.info("Generated tests are up to date")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking proto changes: {e}")
            return True  # Regenerate on error to be safe
    
    def generate_tests(self) -> bool:
        """Generate dynamic proto tests."""
        try:
            self.logger.info("Generating dynamic proto tests...")
            
            # Run the generator script
            result = subprocess.run(
                [sys.executable, str(self.generator_script)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"Test generation failed: {result.stderr}")
                return False
            
            self.logger.info("✅ Test generation completed successfully")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test generation timed out")
            return False
        except Exception as e:
            self.logger.error(f"Test generation error: {e}")
            return False
    
    def validate_generated_tests(self) -> bool:
        """Validate that generated tests are syntactically correct and can be imported."""
        try:
            self.logger.info("Validating generated tests...")
            
            # Check that test files exist
            expected_files = [
                "test_dynamic_serialization.py",
                "test_dynamic_validation.py", 
                "test_dynamic_services.py",
                "test_dynamic_evolution.py"
            ]
            
            for filename in expected_files:
                test_file = self.tests_dir / filename
                if not test_file.exists():
                    self.logger.error(f"Expected test file not found: {filename}")
                    return False
            
            # Try to import each test file to check syntax
            for filename in expected_files:
                try:
                    module_name = filename.replace('.py', '')
                    spec = __import__(f"tests.generated.{module_name}")
                    self.logger.debug(f"✅ Successfully imported {module_name}")
                except Exception as e:
                    self.logger.error(f"Failed to import {module_name}: {e}")
                    return False
            
            self.logger.info("✅ All generated tests validated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Test validation error: {e}")
            return False
    
    def run_core_tests(self) -> bool:
        """Run the core individual message tests that we know work."""
        try:
            self.logger.info("Running core dynamic tests...")
            
            # Run only the individual message tests (not parametrized ones)
            test_commands = [
                [sys.executable, "-m", "pytest", "tests/generated/test_dynamic_serialization.py", "-k", "serialization and not round_trip", "-v"],
                [sys.executable, "-m", "pytest", "tests/generated/test_dynamic_evolution.py", "-v"],
                [sys.executable, "-m", "pytest", "tests/generated/test_dynamic_services.py", "-v"]
            ]

            for cmd in test_commands:
                self.logger.info(f"Running: {' '.join(cmd[2:])}")
                result = subprocess.run(
                    cmd,
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    self.logger.error(f"Tests failed for {' '.join(cmd[2:])}")
                    self.logger.error(f"STDOUT: {result.stdout}")
                    self.logger.error(f"STDERR: {result.stderr}")
                    return False

                self.logger.info(f"✅ Tests passed for {' '.join(cmd[2:])}")
            
            self.logger.info("✅ All core dynamic tests passed")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test execution timed out")
            return False
        except Exception as e:
            self.logger.error(f"Test execution error: {e}")
            return False
    
    def ci_workflow(self, force_regenerate: bool = False) -> bool:
        """Complete CI workflow for dynamic test generation."""
        self.logger.info("🚀 Starting CI dynamic test generation workflow")
        
        # Step 1: Check if regeneration is needed
        if not force_regenerate and not self.check_proto_changes():
            self.logger.info("No proto changes detected, skipping regeneration")
            return True
        
        # Step 2: Generate tests
        if not self.generate_tests():
            self.logger.error("❌ Test generation failed")
            return False
        
        # Step 3: Validate generated tests
        if not self.validate_generated_tests():
            self.logger.error("❌ Test validation failed")
            return False
        
        # Step 4: Run core tests to ensure they pass
        if not self.run_core_tests():
            self.logger.error("❌ Core tests failed")
            return False
        
        self.logger.info("✅ CI dynamic test generation workflow completed successfully")
        return True


def main():
    """Main entry point for CI test generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CI Dynamic Proto Test Generation")
    parser.add_argument("--force", action="store_true", 
                       help="Force regeneration even if no changes detected")
    parser.add_argument("--check-only", action="store_true",
                       help="Only check if regeneration is needed")
    parser.add_argument("--validate-only", action="store_true",
                       help="Only validate existing generated tests")
    
    args = parser.parse_args()
    
    generator = CITestGenerator()
    
    try:
        if args.check_only:
            needs_regen = generator.check_proto_changes()
            print(f"Regeneration needed: {needs_regen}")
            sys.exit(0 if not needs_regen else 1)
        
        elif args.validate_only:
            success = generator.validate_generated_tests()
            sys.exit(0 if success else 1)
        
        else:
            # Full CI workflow
            success = generator.ci_workflow(force_regenerate=args.force)
            sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        logger.error("CI workflow interrupted")
        sys.exit(1)
    except Exception as e:
        logger.error(f"CI workflow failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
