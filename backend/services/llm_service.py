import json
import os
from typing import Dict, List, Any, Optional
import anthropic
import traceback
import logging
import time
from anthropic import Anthropic
from config import Config

from models.schema import Schema

# Create a logger for this module
logger = logging.getLogger(__name__)

class LLMService:
    """Service for integrating with Claude API."""
    
    def __init__(self):
        """Initialize the LLM service."""
        logger.info("Initializing LLMService")
        
        # Get Claude API key
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            logger.warning("No Anthropic API key found in environment variables. LLM extraction will not work.")
        else:
            logger.info("Anthropic API key found")
            
        # Initialize the Anthropic client with the new API pattern
        self.client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.model = "claude-3-7-sonnet-latest"  # Using Claude 3.7 Sonnet
        
        # Print the version for debugging
        try:
            import pkg_resources
            version = pkg_resources.get_distribution("anthropic").version
            logger.info(f"Using Anthropic SDK version: {version}")
            logger.info(f"Using model: {self.model}")
        except Exception as e:
            logger.error(f"Could not determine Anthropic SDK version: {e}")
    
    def format_prompt(self, text: str, schema: Schema) -> str:
        """Create a prompt for Claude based on schema.
        
        Args:
            text: Extracted text from the document
            schema: Schema to apply
            
        Returns:
            Formatted prompt for Claude
        """
        # Create a description of each field
        field_descriptions = "\n".join([
            f"{i+1}. {field.name}: {field.description}"
            for i, field in enumerate(schema.fields)
        ])
        
        # Create the prompt for Anthropic format
        prompt = f"""I have a document that appears to be a {schema.name}. I need to extract specific information from it.

Here's the extracted text from the document:
{text}

Please extract the following information according to these field descriptions:
{field_descriptions}

For each field, provide:
1. The extracted value
2. The confidence in your extraction (high, medium, low)
3. The exact text snippet from the document that contains this information
4. The page number where this information appears (if available)

Format your response as a JSON object with the following structure:
```
{{
  "field_name": {{
    "value": "extracted value",
    "confidence": "high/medium/low",
    "source_text": "text from document",
    "page": page_number
  }},
  ...
}}
```"""
        return prompt
    
    def extract_information(self, text: str, schema: dict) -> Optional[dict]:
        """Extract information from text using Claude API."""
        try:
            logging.info(f"Using model {self.model}")
            prompt = self.format_prompt(text, schema)
            
            response = self.client.messages.create(
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0
            )
            
            logging.debug(f"Raw response from Claude: {response}")
            
            # Extract the content from the response
            content = response.content[0].text
            
            # Strip markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                # Parse the JSON response
                extracted_data = json.loads(content)
                logging.debug(f"Extracted JSON data: {extracted_data}")
                return {"extracted_data": extracted_data}
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                logging.error(f"Raw content was: {content}")
                return None
            
        except Exception as e:
            logging.error(f"Error in extract_information: {str(e)}")
            logging.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    def _build_extraction_prompt(self, text, schema):
        """Build the prompt for Claude to extract information."""
        fields = schema.get("fields", {})
        field_descriptions = []
        
        for field_name, field_info in fields.items():
            description = field_info.get("description", "")
            field_type = field_info.get("type", "string")
            field_descriptions.append(f"- {field_name} ({field_type}): {description}")
            
        field_descriptions_str = "\n".join(field_descriptions)
        
        prompt = f"""Extract information from the following text according to the schema below.
        Return ONLY a JSON object with the extracted information. Do not include any other text.
        
        Schema fields:
        {field_descriptions_str}
        
        Text to extract from:
        {text}
        
        Return the extracted information as a JSON object where the keys are the field names and the values are the extracted information.
        If a field cannot be found in the text, set its value to null.
        """
        
        return prompt


# Create a singleton instance
llm_service = LLMService()
