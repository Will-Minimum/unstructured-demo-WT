import os
import json
import logging
from typing import List, Dict, Any, Optional
import glob

from models.schema import Schema, SchemaField

# Create a logger for this module
logger = logging.getLogger(__name__)

class SchemaService:
    """Service for managing extraction schemas."""
    
    def __init__(self, schemas_dir: str = 'schemas'):
        """Initialize the schema service.
        
        Args:
            schemas_dir: Directory containing schema JSON files
        """
        logger.info("Initializing SchemaService")
        
        # Get the absolute path to the schemas directory
        self.schemas_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), schemas_dir)
        self._schemas = None
        
        logger.info(f"Schema directory path: {self.schemas_dir}")
        
        # Create the schema directory if it doesn't exist
        if not os.path.exists(self.schemas_dir):
            logger.info("Creating schema directory")
            os.makedirs(self.schemas_dir)
        
        # Load the schemas
        self._load_schemas()
    
    def _load_schemas(self) -> None:
        """Load all schemas from the schemas directory."""
        logger.info("Loading schemas from config directory")
        
        self._schemas = {}
        schema_files = glob.glob(os.path.join(self.schemas_dir, '*.json'))
        
        logger.info(f"Found {len(schema_files)} schema files")
        
        for schema_file in schema_files:
            try:
                logger.info(f"Loading schema from file: {schema_file}")
                
                with open(schema_file, 'r') as file:
                    schema_data = json.load(file)
                
                # Create a Schema object from the data
                schema = self._create_schema_from_data(schema_data)
                
                # Add the schema to the collection
                self._schemas[schema.id] = schema
                logger.info(f"Loaded schema: {schema.id} ({schema.name})")
                
            except Exception as e:
                logger.exception(f"Error loading schema from file {schema_file}: {e}")
    
    def _create_schema_from_data(self, data: Dict) -> Schema:
        """Create a Schema object from JSON data."""
        logger.debug(f"Creating schema from data: {json.dumps(data, indent=2)}")
        
        # Extract the schema fields
        fields = []
        
        if 'fields' in data:
            for field_data in data['fields']:
                field = SchemaField(
                    name=field_data.get('name', ''),
                    description=field_data.get('description', ''),
                    field_type=field_data.get('type', 'string'),
                    required=field_data.get('required', False)
                )
                fields.append(field)
        
        # Create the Schema object
        schema = Schema(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            fields=fields
        )
        
        logger.debug(f"Created schema with {len(fields)} fields")
        return schema
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get a list of all available schemas.
        
        Returns:
            List of schema metadata (id, name, description)
        """
        logger.info("Getting all schemas")
        
        if self._schemas is None:
            self._load_schemas()
        
        schemas_list = []
        
        for schema_id, schema in self._schemas.items():
            schemas_list.append({
                'id': schema.id,
                'name': schema.name,
                'description': schema.description
            })
        
        logger.info(f"Returning {len(schemas_list)} schemas")
        return schemas_list
    
    def get_schema_by_id(self, schema_id: str) -> Optional[Schema]:
        """Get a specific schema by ID.
        
        Args:
            schema_id: ID of the schema to retrieve
            
        Returns:
            Schema object if found, None otherwise
        """
        logger.info(f"Getting schema by ID: {schema_id}")
        
        if self._schemas is None:
            self._load_schemas()
        
        if schema_id in self._schemas:
            schema = self._schemas[schema_id]
            logger.info(f"Found schema: {schema.name}")
            return schema
        else:
            logger.warning(f"Schema not found with ID: {schema_id}")
            return None
    
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """Validate a schema's structure.
        
        Args:
            schema: Schema dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_keys = ["id", "name", "description", "fields"]
        if not all(key in schema for key in required_keys):
            return False
        
        if not isinstance(schema["fields"], list):
            return False
        
        for field in schema["fields"]:
            if not all(key in field for key in ["name", "description", "type"]):
                return False
        
        return True

    def save_schema(self, schema: Schema) -> bool:
        """Save a schema to the config directory."""
        logger.info(f"Saving schema: {schema.id} ({schema.name})")
        
        try:
            # Convert the schema to a dictionary
            schema_data = schema.to_dict()
            
            # Create the file path
            filename = f"{schema.id}.json"
            file_path = os.path.join(self.schemas_dir, filename)
            
            # Save the schema to the file
            with open(file_path, 'w') as file:
                json.dump(schema_data, file, indent=2)
            
            # Add the schema to the collection
            self._schemas[schema.id] = schema
            
            logger.info(f"Schema saved to file: {file_path}")
            return True
            
        except Exception as e:
            logger.exception(f"Error saving schema {schema.id}: {e}")
            return False
    
    def delete_schema(self, schema_id: str) -> bool:
        """Delete a schema by its ID."""
        logger.info(f"Deleting schema: {schema_id}")
        
        if schema_id not in self._schemas:
            logger.warning(f"Schema not found with ID: {schema_id}")
            return False
        
        try:
            # Remove the schema from the collection
            schema = self._schemas.pop(schema_id)
            
            # Remove the schema file
            filename = f"{schema_id}.json"
            file_path = os.path.join(self.schemas_dir, filename)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Schema file deleted: {file_path}")
            
            logger.info(f"Schema deleted: {schema.name}")
            return True
            
        except Exception as e:
            logger.exception(f"Error deleting schema {schema_id}: {e}")
            return False

# Create a singleton instance
schema_service = SchemaService()
