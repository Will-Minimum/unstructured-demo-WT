import json
import os
from typing import Dict, List, Optional, Any

class SchemaField:
    """Represents a field in an extraction schema."""
    
    def __init__(self, name: str, description: str, field_type: str, required: bool = False):
        """Initialize a schema field.
        
        Args:
            name: Field name
            description: Field description
            field_type: Field data type (string, number, etc.)
            required: Whether the field is required
        """
        self.name = name
        self.description = description
        self.type = field_type  # Stored as 'type' in the object
        self.required = required
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the field to a dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,  # Exported as 'type' in JSON
            "required": self.required
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SchemaField':
        """Create a SchemaField from a dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            field_type=data["type"],  # Map 'type' from JSON to field_type parameter
            required=data.get("required", False)
        )


class Schema:
    """Represents an extraction schema."""
    
    def __init__(self, id: str = None, schema_id: str = None, name: str = "", description: str = "", fields: List[SchemaField] = None):
        """Initialize a schema.
        
        Args:
            id: Schema ID (primary)
            schema_id: Schema ID (alternative parameter name)
            name: Schema name
            description: Schema description
            fields: List of schema fields
        """
        # Handle either id or schema_id parameter
        self.id = id if id is not None else schema_id
        self.name = name
        self.description = description
        self.fields = fields or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the schema to a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "fields": [field.to_dict() for field in self.fields]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Schema':
        """Create a Schema from a dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            fields=[SchemaField.from_dict(field) for field in data["fields"]]
        )
    
    @classmethod
    def from_json_file(cls, file_path: str) -> 'Schema':
        """Load a schema from a JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
