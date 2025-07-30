#!/usr/bin/env python
"""Generate FastAPI services and routes from protobuf definitions."""

import os
import sys
from pathlib import Path
import importlib.util

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from postfiat.logging import get_logger


def generate_service_layer():
    """Generate service layer classes from protobuf message definitions."""
    
    # Import the generated protobuf module
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    try:
        from postfiat.v3 import messages_pb2, errors_pb2
    except ImportError as e:
        print(f"Error: Could not import generated protobuf files: {e}")
        print("Make sure to run 'buf generate' first")
        return False
    
    print("🔍 Generating service layer from protobuf message definitions...")
    
    # Start building the service code
    service_code = '''"""Auto-generated service layer from protobuf definitions.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_fastapi_services.py' to regenerate.
"""

from typing import Optional, List, Dict, Any
from sqlmodel import Session, select
from postfiat.models.generated import *
from postfiat.logging import get_logger


class BaseService:
    """Base service class with common CRUD operations."""
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = get_logger(f"services.{self.__class__.__name__.lower()}")


'''
    
    # Discover message types
    protobuf_modules = [
        ('messages_pb2', messages_pb2),
        ('errors_pb2', errors_pb2)
    ]
    
    message_types = {}
    for module_name, module in protobuf_modules:
        print(f"🔍 Scanning {module_name} for message types...")
        for name in dir(module):
            if not name.startswith('_') and not name.endswith('_pb2'):
                attr = getattr(module, name)
                if hasattr(attr, 'DESCRIPTOR') and hasattr(attr.DESCRIPTOR, 'fields'):
                    message_types[name] = attr
                    print(f"📊 Found message type: {name} in {module_name}")
    
    if not message_types:
        print("⚠️  No message types found in protobuf modules")
        return False
    
    # Generate service classes for each message type
    for message_name, message_type in message_types.items():
        print(f"📝 Generating service for {message_name}")
        
        # Skip certain message types
        if message_name in ['ExceptionDefinition']:
            continue
            
        service_name = f"{message_name}Service"
        
        # Generate the service class
        service_code += f'class {service_name}(BaseService):\n'
        service_code += f'    """Service for {message_name} operations."""\n\n'
        
        # Create method
        service_code += f'    async def create_{message_name.lower()}(self, data: {message_name}) -> {message_name}:\n'
        service_code += f'        """Create a new {message_name}."""\n'
        service_code += f'        self.logger.info("Creating {message_name}", model_data=data.model_dump())\n'
        service_code += f'        \n'
        service_code += f'        self.session.add(data)\n'
        service_code += f'        self.session.commit()\n'
        service_code += f'        self.session.refresh(data)\n'
        service_code += f'        \n'
        service_code += f'        self.logger.info("Created {message_name}", model_id=data.id)\n'
        service_code += f'        return data\n\n'
        
        # Get by ID method
        service_code += f'    async def get_{message_name.lower()}_by_id(self, id: int) -> Optional[{message_name}]:\n'
        service_code += f'        """Get {message_name} by ID."""\n'
        service_code += f'        self.logger.debug("Getting {message_name} by ID", model_id=id)\n'
        service_code += f'        \n'
        service_code += f'        statement = select({message_name}).where({message_name}.id == id)\n'
        service_code += f'        result = self.session.exec(statement).first()\n'
        service_code += f'        \n'
        service_code += f'        if result:\n'
        service_code += f'            self.logger.debug("Found {message_name}", model_id=id)\n'
        service_code += f'        else:\n'
        service_code += f'            self.logger.warning("{message_name} not found", model_id=id)\n'
        service_code += f'        \n'
        service_code += f'        return result\n\n'
        
        # List method
        service_code += f'    async def list_{message_name.lower()}s(self, skip: int = 0, limit: int = 100) -> List[{message_name}]:\n'
        service_code += f'        """List {message_name}s with pagination."""\n'
        service_code += f'        self.logger.debug("Listing {message_name}s", skip=skip, limit=limit)\n'
        service_code += f'        \n'
        service_code += f'        statement = select({message_name}).offset(skip).limit(limit)\n'
        service_code += f'        results = self.session.exec(statement).all()\n'
        service_code += f'        \n'
        service_code += f'        self.logger.info("Listed {message_name}s", count=len(results), skip=skip, limit=limit)\n'
        service_code += f'        return results\n\n'
        
        # Update method
        service_code += f'    async def update_{message_name.lower()}(self, id: int, data: Dict[str, Any]) -> Optional[{message_name}]:\n'
        service_code += f'        """Update {message_name} by ID."""\n'
        service_code += f'        self.logger.info("Updating {message_name}", model_id=id, update_fields=list(data.keys()))\n'
        service_code += f'        \n'
        service_code += f'        db_obj = await self.get_{message_name.lower()}_by_id(id)\n'
        service_code += f'        if not db_obj:\n'
        service_code += f'            self.logger.warning("{message_name} not found for update", model_id=id)\n'
        service_code += f'            return None\n'
        service_code += f'        \n'
        service_code += f'        for field, value in data.items():\n'
        service_code += f'            if hasattr(db_obj, field):\n'
        service_code += f'                setattr(db_obj, field, value)\n'
        service_code += f'        \n'
        service_code += f'        from datetime import datetime\n'
        service_code += f'        db_obj.updated_at = datetime.utcnow()\n'
        service_code += f'        \n'
        service_code += f'        self.session.add(db_obj)\n'
        service_code += f'        self.session.commit()\n'
        service_code += f'        self.session.refresh(db_obj)\n'
        service_code += f'        \n'
        service_code += f'        self.logger.info("Updated {message_name}", model_id=id)\n'
        service_code += f'        return db_obj\n\n'
        
        # Delete method
        service_code += f'    async def delete_{message_name.lower()}(self, id: int) -> bool:\n'
        service_code += f'        """Delete {message_name} by ID."""\n'
        service_code += f'        self.logger.info("Deleting {message_name}", model_id=id)\n'
        service_code += f'        \n'
        service_code += f'        db_obj = await self.get_{message_name.lower()}_by_id(id)\n'
        service_code += f'        if not db_obj:\n'
        service_code += f'            self.logger.warning("{message_name} not found for deletion", model_id=id)\n'
        service_code += f'            return False\n'
        service_code += f'        \n'
        service_code += f'        self.session.delete(db_obj)\n'
        service_code += f'        self.session.commit()\n'
        service_code += f'        \n'
        service_code += f'        self.logger.info("Deleted {message_name}", model_id=id)\n'
        service_code += f'        return True\n\n\n'
    
    # Write the generated file
    output_path = Path(__file__).parent.parent / "postfiat" / "services" / "generated.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(service_code)
    
    print(f"✅ Generated {output_path}")
    return True


def generate_fastapi_routes():
    """Generate FastAPI routes from protobuf message definitions."""

    # Import the generated protobuf module
    sys.path.insert(0, str(Path(__file__).parent.parent))

    try:
        from postfiat.v3 import messages_pb2, errors_pb2
    except ImportError as e:
        print(f"Error: Could not import generated protobuf files: {e}")
        print("Make sure to run 'buf generate' first")
        return False

    print("🔍 Generating FastAPI routes from protobuf message definitions...")

    # Start building the routes code
    routes_code = '''"""Auto-generated FastAPI routes from protobuf definitions.

DO NOT EDIT - This file is auto-generated from proto files.
Run 'python scripts/generate_fastapi_services.py' to regenerate.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from postfiat.models.generated import *
from postfiat.services.generated import *
from postfiat.logging import get_logger

# Create router
router = APIRouter()
logger = get_logger("api.generated_routes")


def get_session() -> Session:
    """Dependency to get database session."""
    # This will be implemented by the application
    raise NotImplementedError("Database session dependency not implemented")


'''

    # Discover message types
    protobuf_modules = [
        ('messages_pb2', messages_pb2),
        ('errors_pb2', errors_pb2)
    ]

    message_types = {}
    for module_name, module in protobuf_modules:
        for name in dir(module):
            if not name.startswith('_') and not name.endswith('_pb2'):
                attr = getattr(module, name)
                if hasattr(attr, 'DESCRIPTOR') and hasattr(attr.DESCRIPTOR, 'fields'):
                    message_types[name] = attr

    # Generate routes for each message type
    for message_name, message_type in message_types.items():
        print(f"📝 Generating routes for {message_name}")

        # Skip certain message types
        if message_name in ['ExceptionDefinition']:
            continue

        service_name = f"{message_name}Service"
        endpoint_name = message_name.lower()

        # Create endpoint
        routes_code += f'@router.post("/{endpoint_name}s/", response_model={message_name})\n'
        routes_code += f'async def create_{endpoint_name}(\n'
        routes_code += f'    data: {message_name},\n'
        routes_code += f'    session: Session = Depends(get_session)\n'
        routes_code += f') -> {message_name}:\n'
        routes_code += f'    """Create a new {message_name}."""\n'
        routes_code += f'    logger.info("API request to create {message_name}")\n'
        routes_code += f'    \n'
        routes_code += f'    service = {service_name}(session)\n'
        routes_code += f'    try:\n'
        routes_code += f'        result = await service.create_{endpoint_name}(data)\n'
        routes_code += f'        logger.info("Successfully created {message_name}", model_id=result.id)\n'
        routes_code += f'        return result\n'
        routes_code += f'    except Exception as e:\n'
        routes_code += f'        logger.error("Failed to create {message_name}", error=str(e))\n'
        routes_code += f'        raise HTTPException(\n'
        routes_code += f'            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,\n'
        routes_code += f'            detail=f"Failed to create {message_name}: {{str(e)}}"\n'
        routes_code += f'        )\n\n'

        # Get by ID endpoint
        routes_code += f'@router.get("/{endpoint_name}s/{{id}}", response_model={message_name})\n'
        routes_code += f'async def get_{endpoint_name}(\n'
        routes_code += f'    id: int,\n'
        routes_code += f'    session: Session = Depends(get_session)\n'
        routes_code += f') -> {message_name}:\n'
        routes_code += f'    """Get {message_name} by ID."""\n'
        routes_code += f'    logger.info("API request to get {message_name}", model_id=id)\n'
        routes_code += f'    \n'
        routes_code += f'    service = {service_name}(session)\n'
        routes_code += f'    result = await service.get_{endpoint_name}_by_id(id)\n'
        routes_code += f'    \n'
        routes_code += f'    if not result:\n'
        routes_code += f'        logger.warning("{message_name} not found", model_id=id)\n'
        routes_code += f'        raise HTTPException(\n'
        routes_code += f'            status_code=status.HTTP_404_NOT_FOUND,\n'
        routes_code += f'            detail=f"{message_name} with id {{id}} not found"\n'
        routes_code += f'        )\n'
        routes_code += f'    \n'
        routes_code += f'    logger.info("Successfully retrieved {message_name}", model_id=id)\n'
        routes_code += f'    return result\n\n'

        # List endpoint
        routes_code += f'@router.get("/{endpoint_name}s/", response_model=List[{message_name}])\n'
        routes_code += f'async def list_{endpoint_name}s(\n'
        routes_code += f'    skip: int = 0,\n'
        routes_code += f'    limit: int = 100,\n'
        routes_code += f'    session: Session = Depends(get_session)\n'
        routes_code += f') -> List[{message_name}]:\n'
        routes_code += f'    """List {message_name}s with pagination."""\n'
        routes_code += f'    logger.info("API request to list {message_name}s", skip=skip, limit=limit)\n'
        routes_code += f'    \n'
        routes_code += f'    service = {service_name}(session)\n'
        routes_code += f'    results = await service.list_{endpoint_name}s(skip=skip, limit=limit)\n'
        routes_code += f'    \n'
        routes_code += f'    logger.info("Successfully listed {message_name}s", count=len(results))\n'
        routes_code += f'    return results\n\n'

        # Update endpoint
        routes_code += f'@router.put("/{endpoint_name}s/{{id}}", response_model={message_name})\n'
        routes_code += f'async def update_{endpoint_name}(\n'
        routes_code += f'    id: int,\n'
        routes_code += f'    data: Dict[str, Any],\n'
        routes_code += f'    session: Session = Depends(get_session)\n'
        routes_code += f') -> {message_name}:\n'
        routes_code += f'    """Update {message_name} by ID."""\n'
        routes_code += f'    logger.info("API request to update {message_name}", model_id=id)\n'
        routes_code += f'    \n'
        routes_code += f'    service = {service_name}(session)\n'
        routes_code += f'    result = await service.update_{endpoint_name}(id, data)\n'
        routes_code += f'    \n'
        routes_code += f'    if not result:\n'
        routes_code += f'        logger.warning("{message_name} not found for update", model_id=id)\n'
        routes_code += f'        raise HTTPException(\n'
        routes_code += f'            status_code=status.HTTP_404_NOT_FOUND,\n'
        routes_code += f'            detail=f"{message_name} with id {{id}} not found"\n'
        routes_code += f'        )\n'
        routes_code += f'    \n'
        routes_code += f'    logger.info("Successfully updated {message_name}", model_id=id)\n'
        routes_code += f'    return result\n\n'

        # Delete endpoint
        routes_code += f'@router.delete("/{endpoint_name}s/{{id}}")\n'
        routes_code += f'async def delete_{endpoint_name}(\n'
        routes_code += f'    id: int,\n'
        routes_code += f'    session: Session = Depends(get_session)\n'
        routes_code += f') -> Dict[str, str]:\n'
        routes_code += f'    """Delete {message_name} by ID."""\n'
        routes_code += f'    logger.info("API request to delete {message_name}", model_id=id)\n'
        routes_code += f'    \n'
        routes_code += f'    service = {service_name}(session)\n'
        routes_code += f'    success = await service.delete_{endpoint_name}(id)\n'
        routes_code += f'    \n'
        routes_code += f'    if not success:\n'
        routes_code += f'        logger.warning("{message_name} not found for deletion", model_id=id)\n'
        routes_code += f'        raise HTTPException(\n'
        routes_code += f'            status_code=status.HTTP_404_NOT_FOUND,\n'
        routes_code += f'            detail=f"{message_name} with id {{id}} not found"\n'
        routes_code += f'        )\n'
        routes_code += f'    \n'
        routes_code += f'    logger.info("Successfully deleted {message_name}", model_id=id)\n'
        routes_code += f'    return {{"message": f"{message_name} with id {{id}} deleted successfully"}}\n\n'

    # Write the generated file
    output_path = Path(__file__).parent.parent / "postfiat" / "api" / "generated_routes.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write(routes_code)

    print(f"✅ Generated {output_path}")
    return True


def main():
    """Generate FastAPI services from protobuf definitions."""
    print("🔄 Generating FastAPI services from protobuf definitions...")

    success = True
    success &= generate_service_layer()
    success &= generate_fastapi_routes()

    if success:
        print("✅ All FastAPI services generated successfully!")
    else:
        print("❌ Some files failed to generate")
        sys.exit(1)


if __name__ == "__main__":
    main()
