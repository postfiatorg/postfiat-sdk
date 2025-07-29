#!/usr/bin/env python
"""
Developer Test Regeneration Script

Quick script for local development to regenerate proto tests
when working on proto schema changes.
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from postfiat.logging import get_logger

logger = get_logger("dev.test_regen")


def main():
    """Main entry point for developer test regeneration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Developer Test Regeneration")
    # Legacy option removed - old generator no longer exists
    parser.add_argument("--run-tests", action="store_true",
                       help="Run tests after generation")
    parser.add_argument("--core-only", action="store_true",
                       help="Run only core tests that are known to work")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    
    try:
        logger.info(" Using dynamic proto test generator")
        script = "scripts/generate_dynamic_protobuf_tests.py"
        
        # Generate tests
        logger.info(f"Running: {script}")
        subprocess.run(
            [sys.executable, script],
            cwd=project_root,
            check=True
        )
        
        logger.info("✅ Test generation completed")
        
        if args.run_tests:
            logger.info("🧪 Running generated tests...")
            
            if args.core_only:
                # Run only the core tests that work
                test_commands = [
                    ["python", "-m", "pytest", "tests/generated/test_dynamic_serialization.py", "-k", "serialization and not round_trip", "-v"],
                    ["python", "-m", "pytest", "tests/generated/test_dynamic_evolution.py", "-v"],
                    ["python", "-m", "pytest", "tests/generated/test_dynamic_services.py", "-v"]
                ]
                
                for cmd in test_commands:
                    logger.info(f"Running: {' '.join(cmd)}")
                    subprocess.run(cmd, cwd=project_root, check=True)
            else:
                # Run all generated tests
                subprocess.run(
                    ["python", "-m", "pytest", "tests/generated/", "-v"],
                    cwd=project_root,
                    check=True
                )
            
            logger.info("✅ Tests completed")
        
        logger.info("🎉 Development test regeneration complete!")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Command failed with exit code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.error("❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
