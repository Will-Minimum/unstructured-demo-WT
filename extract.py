#!/usr/bin/env python3
import os
import json
import argparse
import requests
import logging
import uuid
import sys
import vcr
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Import PyMuPDF at the module level
try:
    import fitz  # PyMuPDF
except ImportError:
    logging.warning("PyMuPDF (fitz) not installed. PDF annotation will not be available.")
    logging.warning("Please install with: pip install pymupdf")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load environment variables from backend/.env file
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, 'backend', '.env')
if os.path.exists(env_path):
    logger.info(f"Loading environment variables from: {env_path}")
    load_dotenv(env_path)
    logger.info("Environment variables loaded successfully")
else:
    logger.warning(f".env file not found at {env_path}. Using system environment variables.")

# Create cassettes directory if it doesn't exist
cassettes_dir = os.path.join(script_dir, 'cassettes')
os.makedirs(cassettes_dir, exist_ok=True)

class PDFExtractor:
    """Process PDFs and extract structured information based on schemas."""
    
    def __init__(self, api_key=None, api_url=None, skip_validation=False, use_recorded=False, force_new_requests=False):
        """Initialize the extractor with API credentials."""
        self.api_key = api_key or os.environ.get("UNSTRUCTURED_API_KEY")
        self.api_url = api_url or os.environ.get("UNSTRUCTURED_API_URL", "https://api.unstructuredapp.io/general/v0/general")
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.skip_validation = skip_validation
        self.use_recorded = use_recorded
        self.force_new_requests = force_new_requests
        
        if not self.api_key and not self.use_recorded:
            logger.error("UNSTRUCTURED_API_KEY not set. Please set it as an environment variable or pass it as an argument.")
            sys.exit(1)
            
        if not self.anthropic_api_key and not self.use_recorded:
            logger.error("ANTHROPIC_API_KEY not set. Please set it as an environment variable.")
            sys.exit(1)
            
        logger.info(f"Using Unstructured API URL: {self.api_url}")
        
        if not self.skip_validation and not self.use_recorded:
            self._validate_api_key()
        else:
            logger.info("Skipping API key validation")
    
    def _validate_api_key(self) -> bool:
        """Validate the Unstructured API key by making a test request."""
        try:
            logger.info("Testing Unstructured API key...")
            headers = {
                "accept": "application/json",
                "unstructured-api-key": self.api_key
            }
            
            response = requests.get(
                f"{self.api_url}/elements/validate",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 401:
                logger.error(f"API key validation failed: {response.text}")
                sys.exit(1)
            elif response.status_code in (200, 404):
                logger.info("✅ Unstructured API key is valid!")
                return True
            else:
                logger.warning(f"API key validation returned unexpected status code: {response.status_code}")
                logger.warning(f"Response: {response.text}")
                return True
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error validating API key: {e}")
            logger.warning("Continuing despite validation error...")
            return False
    
    def process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a PDF using Unstructured API, with recording/replay support."""
        logger.info(f"Processing PDF: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        
        # Create a cassette name based on the file name
        file_name = os.path.basename(file_path)
        cassette_path = os.path.join('cassettes', f"{os.path.splitext(file_name)[0]}_unstructured.yaml")
        
        # Check if we need to force a new recording
        if (os.path.exists(cassette_path) and 
            (self.force_new_requests or not self.use_recorded)):
            logger.info(f"Removing existing cassette file to record new response: {cassette_path}")
            os.remove(cassette_path)
        
        # Configure VCR
        record_mode = 'none' if self.use_recorded else 'new_episodes'
        logger.info(f"Unstructured API VCR record mode: {record_mode}")
        
        my_vcr = vcr.VCR(
            cassette_library_dir='cassettes',
            record_mode=record_mode,
            match_on=['uri', 'method'],
            filter_headers=['unstructured-api-key'],
            decode_compressed_response=True
        )
        
        # If using recorded responses, check if cassette exists
        if self.use_recorded and not os.path.exists(cassette_path):
            logger.error(f"No recorded response found for {file_name}. Run without '--use-recorded-unstructured-response' first.")
            return None
        
        try:
            # Use VCR to record/replay the API request
            with my_vcr.use_cassette(cassette_path):
                logger.info(f"{'Using recorded' if self.use_recorded else 'Recording'} Unstructured API response")
                
                # Prepare the API request
                headers = {
                    "accept": "application/json",
                    "unstructured-api-key": self.api_key
                }
                
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    file_size_mb = len(file_content) / (1024 * 1024)
                    logger.info(f"PDF file size: {file_size_mb:.2f} MB")
                    
                    files = {
                        "files": (os.path.basename(file_path), file_content, "application/pdf")
                    }
                    
                    data = {
                        "strategy": "hi_res",
                        "coordinates": "true",
                        "split_pdf_page": "true",
                        "split_pdf_allow_failed": "true",
                        "split_pdf_concurrency_level": "15"
                    }
                    
                    logger.info("Sending request to Unstructured API - this may take some time for large documents...")
                    
                    response = requests.post(
                        f"{self.api_url}",
                        headers=headers,
                        files=files,
                        data=data,
                        timeout=300  # 5 minute timeout
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"API request failed with status code {response.status_code}")
                        logger.error(f"Response: {response.text}")
                        return None
                    
                    elements = response.json()
                    logger.info(f"PDF processed successfully, received {len(elements)} elements")
                    
                    # Log element types
                    element_types = {}
                    for element in elements:
                        element_type = element["type"]
                        element_types[element_type] = element_types.get(element_type, 0) + 1
                    
                    logger.info(f"Element types found: {json.dumps(element_types, indent=2)}")
                    
                    # Save the response to a file for easier review
                    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_responses')
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_unstructured_response.json")
                    with open(output_file, 'w') as f:
                        json.dump(elements, f, indent=2)
                    logger.info(f"Saved Unstructured API response to: {output_file}")
                    
                    return elements
                    
        except Exception as e:
            logger.exception(f"Error processing PDF: {e}")
            return None
    
    def load_schema(self, schema_path: str) -> Dict:
        """Load a schema from a JSON file."""
        logger.info(f"Loading schema from: {schema_path}")
        
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            
            logger.info(f"Schema loaded: {schema['name']}")
            return schema
        except Exception as e:
            logger.exception(f"Error loading schema: {e}")
            sys.exit(1)
    
    def format_extraction_prompt(self, elements: List[Dict], schema: Dict) -> str:
        """Create a prompt for Claude based on schema, including structured element data.
        
        Args:
            elements: The structured elements from Unstructured.io
            schema: The extraction schema
            
        Returns:
            Formatted prompt for Claude
        """
        # Create a description of each field
        field_descriptions = "\n".join([
            f"{i+1}. {field['name']}: {field['description']}"
            for i, field in enumerate(schema['fields'])
        ])
        
        # Filter out potentially unnecessary fields to reduce token usage
        simplified_elements = []
        for element in elements:
            # Keep only essential fields for each element
            simplified_element = {
                "type": element.get("type", ""),
                "text": element.get("text", ""),
                "metadata": element.get("metadata", {})
            }
            
            # Keep coordinates if available
            if "coordinates" in element:
                simplified_element["coordinates"] = element["coordinates"]
                
            simplified_elements.append(simplified_element)
        
        # Convert elements to JSON string
        elements_json = json.dumps(simplified_elements, indent=2)
        
        # Create the prompt
        prompt = f"""I have a document that appears to be a {schema['name']}. I need to extract specific information from it.

Here's a structured JSON document that has been extracted using Unstructured.io:
```
{elements_json}
```

Please extract the following information according to these field descriptions:
{field_descriptions}

For each field, provide:
1. The extracted value
2. The confidence in your extraction (high, medium, low)
3. The exact text snippet from the document that contains this information
4. The page number where this information appears (if available)
5. The coordinates where this information appears - IMPORTANT: Include the exact coordinates structure from the JSON document for this field, do not modify or simplify the coordinates

Format your response as a JSON object with the following structure:
```
{{
  "field_name": {{
    "value": "extracted value",
    "confidence": "high/medium/low",
    "source_text": "text from document",
    "page": page_number,
    "coordinates": {{
        "points": [
          [
            x1,
            y1
          ],
          [
            x2,
            y2
          ],
          [
            x3,
            y3
          ],
          [
            x4,
            y4
          ]
        ],
        "system": ["PixelSpace"],
        "layout_width": int,
        "layout_height": int
      }}
  }},
  ...
}}
```

VERY IMPORTANT: For the coordinates field, copy the EXACT coordinates from the matching text element in the JSON document. I need the exact x,y values for all four corner points to highlight the proper areas. Do not modify or simplify these values.
"""
        return prompt
    
    def extract_information(self, elements: List[Dict], schema: Dict) -> Optional[Dict]:
        """Extract information from elements using Claude API."""
        try:
            # Create prompt for Claude with the structured elements data
            prompt = self.format_extraction_prompt(elements, schema)
            
            # Create a safe filename from the schema name
            schema_name = schema.get('name', 'unknown')
            safe_name = ''.join(c if c.isalnum() else '_' for c in schema_name).lower()
            
            # Save the prompt to a file for easier review
            file_name = f"{safe_name}_claude_prompt.txt"
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_responses')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, file_name)
            with open(output_file, 'w') as f:
                f.write(prompt)
            logger.info(f"Saved Claude prompt to: {output_file}")
            
            # Configure VCR for Claude API
            cassette_path = os.path.join('cassettes', f"{safe_name}_claude.yaml")
            
            # Check if we need to force a new recording
            if (os.path.exists(cassette_path) and 
                (self.force_new_requests or not self.use_recorded)):
                logger.info(f"Removing existing cassette file to record new response: {cassette_path}")
                os.remove(cassette_path)
            
            record_mode = 'none' if self.use_recorded else 'new_episodes'
            logger.info(f"VCR record mode: {record_mode}")
            
            my_vcr = vcr.VCR(
                cassette_library_dir='cassettes',
                record_mode=record_mode,  # Use none when replaying, new_episodes when recording
                match_on=['uri', 'method'],  # Removed 'body' to be less strict
                filter_headers=['x-api-key', 'anthropic-version'],
            )
            
            # Call Claude API with VCR
            with my_vcr.use_cassette(cassette_path):
                logger.info(f"{'Using recorded' if self.use_recorded else 'Recording'} Claude API response")
                
                headers = {
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                    "x-api-key": self.anthropic_api_key
                }
                
                data = {
                    "model": "claude-3-7-sonnet-latest",
                    "max_tokens": 4096,
                    "temperature": 0,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
                
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data,
                    timeout=120
                )
                
                if response.status_code != 200:
                    logger.error(f"Claude API request failed with status code {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return None
                
                response_json = response.json()
                content = response_json["content"][0]["text"]
                
                # Strip markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                
                # Parse the JSON response
                extracted_data = json.loads(content)
                logger.info("Information extracted successfully")
                
                # Save the response to a file for easier review
                file_name = f"{safe_name}_claude_response.json"
                output_file = os.path.join(output_dir, file_name)
                with open(output_file, 'w') as f:
                    json.dump(extracted_data, f, indent=2)
                logger.info(f"Saved Claude response to: {output_file}")
                
                # Also save the raw content before JSON parsing
                raw_file_name = f"{safe_name}_claude_raw_response.txt"
                raw_output_file = os.path.join(output_dir, raw_file_name)
                with open(raw_output_file, 'w') as f:
                    f.write(content)
                logger.info(f"Saved raw Claude response to: {raw_output_file}")
                
                # Log each field and its source text
                logger.info("=== EXTRACTED DATA FROM CLAUDE ===")
                for field_name, field_data in extracted_data.items():
                    source_text = field_data.get("source_text", "N/A")
                    value = field_data.get("value", "N/A")
                    confidence = field_data.get("confidence", "N/A")
                    logger.info(f"Field: {field_name}")
                    logger.info(f"  Value: {value}")
                    logger.info(f"  Confidence: {confidence}")
                    logger.info(f"  Source text: \"{source_text}\"")
                    if "page" in field_data:
                        logger.info(f"  Page: {field_data['page']}")
                    logger.info("---")
                
                return extracted_data
            
        except Exception as e:
            logger.exception(f"Error extracting information: {e}")
            return None
    
    def save_results(self, extracted_data: Dict, output_path: str) -> None:
        """Save the extracted data to a JSON file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(extracted_data, f, indent=2)
            
            logger.info(f"Results saved to: {output_path}")
        except Exception as e:
            logger.exception(f"Error saving results: {e}")
    
    def map_extracted_fields_to_locations(self, extracted_data: Dict, elements: List[Dict]) -> Dict[str, List[Dict]]:
        """Map extracted fields to their locations in the PDF."""
        logger.info("=== MAPPING EXTRACTED FIELDS TO LOCATIONS ===")
        
        # Create a dictionary to hold the field locations
        source_locations = {}
        
        # Save all elements' text content to a file for debugging
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_responses')
        os.makedirs(output_dir, exist_ok=True)
        elements_text_file = os.path.join(output_dir, "all_elements_text.txt")
        with open(elements_text_file, 'w') as f:
            for i, element in enumerate(elements):
                if "text" in element:
                    f.write(f"=== ELEMENT {i+1} ===\n")
                    f.write(f"TYPE: {element.get('type', 'unknown')}\n")
                    if "coordinates" in element:
                        coords = element["coordinates"]
                        page = coords.get("page_number", "unknown")
                        f.write(f"PAGE: {page}\n")
                        if "points" in coords:
                            points = coords["points"]
                            if points:
                                x_values = [p["x"] for p in points]
                                y_values = [p["y"] for p in points]
                                bbox = {
                                    "x0": min(x_values),
                                    "y0": min(y_values),
                                    "x1": max(x_values),
                                    "y1": max(y_values)
                                }
                                f.write(f"BBOX: {json.dumps(bbox)}\n")
                    f.write("TEXT:\n")
                    f.write(element["text"])
                    f.write("\n\n")
        logger.info(f"Saved all elements' text to: {elements_text_file}")
        
        # Log the elements with coordinates
        elements_with_coords = [e for e in elements if "coordinates" in e and "text" in e]
        logger.info(f"Total elements with coordinates: {len(elements_with_coords)}")
        
        # Process each field in the extracted data
        for field_name, field_data in extracted_data.items():
            logger.info(f"\nProcessing field: {field_name}")
            
            # Check if Claude provided coordinates directly
            if "coordinates" in field_data and field_data["coordinates"]:
                logger.info(f"Using coordinates provided by Claude for field '{field_name}'")
                
                try:
                    coords = field_data["coordinates"]
                    page_num = field_data.get("page", 1)  # Default to page 1 if not specified
                    
                    # Handle different possible coordinate formats
                    if "points" in coords:
                        points = coords["points"]
                        raw_points = points  # Save the raw points format
                        
                        # Get layout dimensions if available
                        layout_width = coords.get("layout_width", None)
                        layout_height = coords.get("layout_height", None)
                        coordinate_system = coords.get("system", None)
                        
                        logger.info(f"Coordinate system: {coordinate_system}")
                        logger.info(f"Layout dimensions: {layout_width}x{layout_height}")
                        
                        # Store these for later scaling during annotation
                        coordinate_info = {
                            "system": coordinate_system,
                            "layout_width": layout_width,
                            "layout_height": layout_height
                        }
                        
                        # Check if points is a list of [x,y] lists or a list of {x,y} dicts
                        if points and isinstance(points[0], list):
                            # Convert [x,y] format to x_values and y_values
                            x_values = [p[0] for p in points]
                            y_values = [p[1] for p in points]
                        else:
                            # Assume {x,y} format
                            x_values = [p.get("x", 0) for p in points]
                            y_values = [p.get("y", 0) for p in points]
                        
                        bbox = {
                            "x0": min(x_values),
                            "y0": min(y_values),
                            "x1": max(x_values),
                            "y1": max(y_values)
                        }
                        
                        source_text = field_data.get("source_text", "")
                        
                        # Add to source locations
                        location = {
                            "page_number": page_num,
                            "bounding_box": bbox,
                            "text": source_text,
                            "raw_points": raw_points,
                            "coordinate_info": coordinate_info
                        }
                        source_locations[field_name] = [location]
                        logger.info(f"Added coordinates for field '{field_name}': {bbox}")
                        logger.info(f"Raw points: {raw_points}")
                        continue
                except Exception as e:
                    logger.exception(f"Error processing coordinates for field '{field_name}': {e}")
                    # Fall back to text-based matching
            
            # Fall back to text-based matching if no coordinates or error processing them
            source_text = field_data.get("source_text")
            logger.info(f"Looking for source text: \"{source_text}\"")
            
            if not source_text:
                logger.warning(f"No source text for field '{field_name}', cannot map location")
                continue
                
            # Look for elements containing this text
            found_elements = []
            for i, element in enumerate(elements):
                if "text" not in element or "coordinates" not in element:
                    continue
                    
                element_text = element["text"]
                
                # Check if the source text is in the element text
                if source_text in element_text:
                    # Found a match - get the coordinates
                    coordinates = element["coordinates"]
                    logger.info(f"Found matching element {i+1}:")
                    logger.info(f"  Text: \"{element_text[:100]}...\"" if len(element_text) > 100 else f"  Text: \"{element_text}\"")
                    logger.info(f"  Coordinates: {json.dumps(coordinates, indent=2)}")
                    
                    if not coordinates:
                        logger.warning("  No coordinates in element, skipping")
                        continue
                        
                    # Extract page number and bounding box
                    page_num = coordinates.get("page_number", 1)
                    points = coordinates.get("points", [])
                    
                    if not points or len(points) < 2:
                        logger.warning("  Not enough points in coordinates, skipping")
                        continue
                        
                    # Get the bounding box coordinates
                    x_values = [p["x"] for p in points]
                    y_values = [p["y"] for p in points]
                    
                    x0 = min(x_values)
                    y0 = min(y_values)
                    x1 = max(x_values)
                    y1 = max(y_values)
                    
                    bbox = {
                        "x0": x0,
                        "y0": y0,
                        "x1": x1,
                        "y1": y1
                    }
                    
                    logger.info(f"  Calculated bounding box: {bbox}")
                    
                    # Add to found elements
                    found_elements.append({
                        "page_number": page_num,
                        "bounding_box": bbox,
                        "text": element_text
                    })
            
            # Store the found elements for this field
            if found_elements:
                logger.info(f"Found {len(found_elements)} elements for field '{field_name}'")
                source_locations[field_name] = found_elements
            else:
                logger.warning(f"Could not find any elements for field '{field_name}' with source text: \"{source_text}\"")
                
                # Try to find partial matches for debugging
                logger.info("Attempting to find partial matches for debugging:")
                for i, element in enumerate(elements):
                    if "text" not in element:
                        continue
                    
                    element_text = element["text"]
                    # Check if any words from source_text appear in element_text
                    if any(word in element_text for word in source_text.split() if len(word) > 3):
                        logger.info(f"Partial match in element {i+1}:")
                        logger.info(f"  Text: \"{element_text[:100]}...\"" if len(element_text) > 100 else f"  Text: \"{element_text}\"")
        
        logger.info(f"Total mapped fields: {len(source_locations)}")
        return source_locations
    
    def create_annotated_pdf(self, original_pdf_path: str, source_locations: Dict[str, List[Dict[str, Any]]], 
                           active_field: str = None, flip_y: bool = False, draw_test_points: bool = False, scale: float = 1.0) -> str:
        """Create a new PDF with bounding boxes drawn directly on it."""
        logger.info(f"Creating annotated PDF from {original_pdf_path}")
        
        try:
            from datetime import datetime
            
            # Create a unique filename for the annotated PDF
            file_id = os.path.basename(original_pdf_path).split('.')[0]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            
            # Create upload folder if it doesn't exist
            upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'annotated_pdfs')
            os.makedirs(upload_folder, exist_ok=True)
            
            annotated_pdf_path = os.path.join(upload_folder, f"{file_id}_annotated_{timestamp}.pdf")
            
            # Open the original PDF
            doc = fitz.open(original_pdf_path)
            logger.info(f"Opened PDF with {len(doc)} pages")
            
            # Add a test square to the top-left corner of each page
            logger.info("Adding test square to each page")
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_width = page.rect.width
                page_height = page.rect.height
                
                # Create a red square in the top-left corner (20x20 pixels)
                test_rect = fitz.Rect(20, 20, 40, 40)
                logger.info(f"Adding test square on page {page_idx + 1} at position {test_rect}")
                annot = page.add_rect_annot(test_rect)
                annot.set_colors(stroke=(1, 0, 0))  # Red
                annot.set_border(width=2)
                annot.update()
                logger.info(f"Added test square to page {page_idx + 1}")
                
                # Draw debug info on page - document size
                debug_info = f"Page size: {page_width}x{page_height}"
                page.insert_text(fitz.Point(50, 50), debug_info, fontsize=10, color=(0, 0, 0))
            
            # Log the fields to process
            fields_to_process = [active_field] if active_field else source_locations.keys()
            logger.info(f"Fields to process: {list(fields_to_process)}")
            
            # Process each field
            for field_name in fields_to_process:
                if field_name not in source_locations:
                    logger.warning(f"Field {field_name} not in source_locations, skipping")
                    continue
                
                # Log the number of locations for this field
                locations = source_locations[field_name]
                logger.info(f"Field {field_name} has {len(locations)} locations")
                
                # Get color for this field
                colors = {
                    "invoice_number": (1, 0, 0),  # Red
                    "invoice_date": (0, 1, 0),    # Green
                    "due_date": (0, 0, 1),   # Blue
                    "total_amount": (1, 0.5, 0),     # Orange
                    "account_number": (0.5, 0, 0.5),  # Purple
                    "customer_name": (1, 1, 0),  # Yellow
                    "vendor_name": (0, 0.5, 0.5),  # Teal
                    "tax_amount": (0.5, 0.5, 0),  # Olive
                    "subtotal": (0, 1, 1),  # Cyan
                    "payment_terms": (0.5, 0, 0),  # Maroon
                    
                    # Electricity bill specific
                    "meter_number": (0, 0.5, 0),  # Dark Green
                    "supplier_name": (0.7, 0, 0.7),  # Purple
                    "rate_plan": (0.7, 0.7, 0),  # Dark Yellow
                    "address_of_consuming_site": (0.2, 0.4, 0.6),  # Steel Blue
                    "start_date_of_consumption": (0.6, 0.3, 0),  # Brown
                    "end_date_of_consumption": (0.3, 0.7, 0.7)  # Turquoise
                }
                default_color = (0.5, 0.5, 0.5)  # Gray
                rgb = colors.get(field_name, default_color)
                stroke_color = rgb
                
                # Process each location for this field
                for i, location in enumerate(locations):
                    page_number = location["page_number"] - 1  # 0-based indexing
                    bbox = location["bounding_box"]
                    coordinate_info = location.get("coordinate_info", {})
                    
                    logger.info(f"Processing location {i+1} for field {field_name}:")
                    logger.info(f"  Page number: {page_number + 1}")
                    logger.info(f"  Bounding box: {bbox}")
                    logger.info(f"  Coordinate info: {coordinate_info}")
                    
                    # Skip if page number is out of range
                    if page_number < 0 or page_number >= len(doc):
                        logger.warning(f"Page number {page_number + 1} out of range, skipping")
                        continue
                    
                    # Get the page
                    page = doc[page_number]
                    page_width = page.rect.width
                    page_height = page.rect.height
                    
                    # Get the layout dimensions from coordinate_info if available
                    layout_width = coordinate_info.get("layout_width")
                    layout_height = coordinate_info.get("layout_height")
                    
                    # Get raw points if available
                    raw_points = None
                    if "raw_points" in location and location["raw_points"]:
                        raw_points = location["raw_points"]
                        logger.info(f"  Raw points available: {raw_points}")
                    
                    # Calculate scaling based on layout dimensions if available
                    if layout_width and layout_height and raw_points:
                        logger.info(f"  Using proportional scaling with layout dimensions: {layout_width}x{layout_height}")
                        logger.info(f"  PDF dimensions: {page_width}x{page_height}")
                        
                        # Create a rectangle with properly scaled coordinates
                        scaled_rect = self._get_scaled_rect(raw_points, layout_width, layout_height, page_width, page_height, flip_y)
                        rect = scaled_rect
                        
                        # Log the scaled rectangle
                        logger.info(f"  Proportionally scaled rectangle: {rect}")
                        
                        # Add rectangle annotation
                        annot = page.add_rect_annot(rect)
                        annot.set_colors(stroke=stroke_color)
                        annot.set_border(width=1.5)  # Set line width
                        annot.update()
                        logger.info(f"  Added proportionally scaled rectangle annotation for field {field_name}")
                        
                        # Also draw dots at each corner with proportional scaling
                        if raw_points:
                            self._draw_scaled_points(page, raw_points, layout_width, layout_height, page_width, page_height, flip_y)
                            logger.info(f"  Added proportionally scaled dots for field {field_name}")
                        
                    else:
                        # Create rectangle for the bounding box using manual scaling
                        rect = fitz.Rect(bbox["x0"] * scale, bbox["y0"] * scale, bbox["x1"] * scale, bbox["y1"] * scale)
                        logger.info(f"  PyMuPDF rectangle with manual scaling: {rect}")
                        
                        # Add rectangle annotation
                        annot = page.add_rect_annot(rect)
                        annot.set_colors(stroke=stroke_color)
                        annot.set_border(width=1.5)  # Set line width
                        annot.update()
                        logger.info(f"  Added rectangle annotation for field {field_name}")
                        
                        # Also draw dots at each corner if raw points are available
                        if raw_points:
                            for j, point in enumerate(raw_points):
                                if isinstance(point, list) and len(point) == 2:
                                    x, y = point[0] * scale, point[1] * scale
                                elif isinstance(point, dict) and "x" in point and "y" in point:
                                    x, y = point["x"] * scale, point["y"] * scale
                                else:
                                    logger.warning(f"  Unknown point format: {point}")
                                    continue
                                
                                # Draw dot with manual scaling
                                dot_radius = 4
                                circle = page.new_shape()
                                circle.draw_circle(fitz.Point(x, y), dot_radius)
                                corner_colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1)]
                                color_idx = j % len(corner_colors)
                                circle.finish(fill=corner_colors[color_idx], color=corner_colors[color_idx], width=0.3)
                                logger.info(f"  Added dot {j+1} at manually scaled position ({x}, {y})")
                    
                    # Add text annotation with the field name
                    text_point = fitz.Point(rect.x0, rect.y0 - 10)
                    text_annot = page.add_text_annot(text_point, field_name)
                    text_annot.update()
                    logger.info(f"  Added text annotation for field {field_name}")
            
            # Save the annotated PDF
            logger.info(f"Saving annotated PDF to: {annotated_pdf_path}")
            doc.save(annotated_pdf_path)
            doc.close()
            
            logger.info(f"Annotated PDF saved at: {annotated_pdf_path}")
            return annotated_pdf_path
            
        except Exception as e:
            logger.exception(f"Error creating annotated PDF: {e}")
            return original_pdf_path
            
    def _get_scaled_rect(self, points, layout_width, layout_height, page_width, page_height, flip_y=False):
        """Convert points from layout space to PDF space."""
        scaled_points = []
        
        for point in points:
            if isinstance(point, list) and len(point) == 2:
                x, y = point[0], point[1]
            elif isinstance(point, dict) and "x" in point and "y" in point:
                x, y = point["x"], point["y"]
            else:
                logger.warning(f"Unknown point format: {point}")
                continue
                
            # Scale x and y as proportions of layout dimensions
            scaled_x = (x / layout_width) * page_width
            
            if flip_y:
                # Flip Y coordinate (if Y grows downward in layout but upward in PDF)
                scaled_y = page_height - ((y / layout_height) * page_height)
            else:
                scaled_y = (y / layout_height) * page_height
                
            scaled_points.append((scaled_x, scaled_y))
        
        # Create rectangle from scaled points
        if scaled_points:
            x_values = [p[0] for p in scaled_points]
            y_values = [p[1] for p in scaled_points]
            
            return fitz.Rect(min(x_values), min(y_values), max(x_values), max(y_values))
        else:
            return fitz.Rect(0, 0, 100, 100)  # Default rectangle if no valid points
    
    def _draw_scaled_points(self, page, points, layout_width, layout_height, page_width, page_height, flip_y=False):
        """Draw dots at each point after scaling from layout space to PDF space."""
        dot_radius = 4
        corner_colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1)]
        
        for j, point in enumerate(points):
            if isinstance(point, list) and len(point) == 2:
                x, y = point[0], point[1]
            elif isinstance(point, dict) and "x" in point and "y" in point:
                x, y = point["x"], point["y"]
            else:
                logger.warning(f"Unknown point format: {point}")
                continue
                
            # Scale x and y as proportions of layout dimensions
            scaled_x = (x / layout_width) * page_width
            
            if flip_y:
                # Flip Y coordinate (if Y grows downward in layout but upward in PDF)
                scaled_y = page_height - ((y / layout_height) * page_height)
            else:
                scaled_y = (y / layout_height) * page_height
            
            # Draw a dot at the scaled position
            circle = page.new_shape()
            circle.draw_circle(fitz.Point(scaled_x, scaled_y), dot_radius)
            circle.finish(fill=corner_colors[j % len(corner_colors)], color=corner_colors[j % len(corner_colors)], width=0.3)
            
            # Add a label with the point number and coordinates
            text_point = fitz.Point(scaled_x + dot_radius + 2, scaled_y + dot_radius + 2)
            page.insert_text(text_point, f"{j+1}", fontsize=8, color=(0, 0, 0))
            
            # Add exact coordinates near the point
            coord_point = fitz.Point(scaled_x, scaled_y + 15)
            coord_text = f"({int(scaled_x)},{int(scaled_y)})"
            page.insert_text(coord_point, coord_text, fontsize=6, color=(0, 0, 0))
            
            logger.info(f"  Added dot {j+1} at proportionally scaled position ({scaled_x}, {scaled_y})")
        
        # Update is not needed here - shapes are updated when finish() is called
        # and text is immediately rendered with insert_text()

def main():
    """Main function to process command line arguments and run the extraction."""
    parser = argparse.ArgumentParser(description="Extract structured information from PDF documents")
    parser.add_argument("input_file", help="Path to the input PDF file")
    parser.add_argument("schema", help="Path to the schema JSON file or schema ID (invoice, gas_bill, electricity_bill)")
    parser.add_argument("--output", "-o", help="Path to save the extracted data (default: extracted_data.json)",
                        default="extracted_data.json")
    parser.add_argument("--api-key", help="Unstructured API key (defaults to UNSTRUCTURED_API_KEY environment variable)")
    parser.add_argument("--api-url", help="Unstructured API URL (defaults to UNSTRUCTURED_API_URL environment variable)")
    parser.add_argument("--skip-validation", action="store_true", help="Skip API key validation")
    parser.add_argument("--use-recorded-unstructured-response", action="store_true", 
                        help="Use previously recorded API responses instead of making live requests")
    parser.add_argument("--skip-annotated-pdf", action="store_true",
                        help="Skip creating an annotated PDF with bounding boxes for extracted fields")
    parser.add_argument("--test-pdf", action="store_true",
                        help="Create a test PDF with rectangles to verify PDF annotation is working")
    parser.add_argument("--force", action="store_true",
                        help="Force new API requests even if cassettes exist")
    parser.add_argument("--flip-y", action="store_true",
                        help="Flip Y coordinates for PDFs with bottom-origin coordinate system")
    parser.add_argument("--draw-test-points", action="store_true",
                        help="Draw test points at fixed positions instead of using extracted coordinates")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="Scale factor for coordinates (default: 1.0)")
    
    args = parser.parse_args()
    
    # Handle test PDF creation if requested
    if args.test_pdf:
        create_test_pdf(args.input_file)
        return
    
    # Initialize the extractor
    extractor = PDFExtractor(
        api_key=args.api_key, 
        api_url=args.api_url, 
        skip_validation=args.skip_validation,
        use_recorded=args.use_recorded_unstructured_response,
        force_new_requests=args.force
    )
    
    # Handle schema paths or built-in schemas
    schema_path = args.schema
    if args.schema in ["invoice", "gas_bill", "electricity_bill"]:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(script_dir, "backend", "schemas", f"{args.schema}.json")
        if not os.path.exists(schema_path):
            logger.error(f"Built-in schema not found: {args.schema}")
            sys.exit(1)
    
    # Load the schema
    schema = extractor.load_schema(schema_path)
    
    # Process the PDF
    elements = extractor.process_pdf(args.input_file)
    if not elements:
        logger.error("Failed to process PDF")
        sys.exit(1)
    
    # Extract information
    extracted_data = extractor.extract_information(elements, schema)
    if not extracted_data:
        logger.error("Failed to extract information")
        sys.exit(1)
    
    # Save the results
    extractor.save_results(extracted_data, args.output)
    
    # Create annotated PDF by default unless skipped
    if not args.skip_annotated_pdf:
        # Map extracted fields to locations
        source_locations = extractor.map_extracted_fields_to_locations(extracted_data, elements)
        
        # Create annotated PDF
        annotated_pdf_path = extractor.create_annotated_pdf(args.input_file, source_locations, 
                                                          flip_y=args.flip_y,
                                                          draw_test_points=args.draw_test_points,
                                                          scale=args.scale)
        logger.info(f"Annotated PDF created: {annotated_pdf_path}")
    
    # Print a summary
    logger.info("Extraction complete!")
    logger.info(f"Input file: {args.input_file}")
    logger.info(f"Schema: {schema['name']}")
    logger.info(f"Output file: {args.output}")
    
    # Print the extracted fields
    logger.info("\nExtracted fields:")
    for field, data in extracted_data.items():
        logger.info(f"  {field}: {data.get('value')} (confidence: {data.get('confidence', 'N/A')})")

def create_test_pdf(input_file: str) -> None:
    """Create a test PDF with rectangles to verify annotation is working.
    
    Args:
        input_file: Path to the input PDF file
    """
    from datetime import datetime
    
    logger.info(f"Creating test PDF from {input_file}")
    
    try:
        # Create a unique filename for the test PDF
        file_id = os.path.basename(input_file).split('.')[0]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Create output folder if it doesn't exist
        output_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'annotated_pdfs')
        os.makedirs(output_folder, exist_ok=True)
        
        test_pdf_path = os.path.join(output_folder, f"{file_id}_test_{timestamp}.pdf")
        
        # Open the original PDF
        doc = fitz.open(input_file)
        logger.info(f"Opened PDF with {len(doc)} pages")
        
        # Add test rectangles to each page
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            page_width = page.rect.width
            page_height = page.rect.height
            
            logger.info(f"Page {page_idx + 1} dimensions: {page_width} x {page_height}")
            
            # Add rectangles of different colors in different positions
            # Top-left corner - red
            rect1 = fitz.Rect(20, 20, 70, 70)
            logger.info(f"Adding red square on page {page_idx + 1} at position {rect1}")
            annot1 = page.add_rect_annot(rect1)
            annot1.set_colors(stroke=(1, 0, 0))  # Red
            annot1.set_border(width=2)
            annot1.update()
            
            # Top-right corner - green
            rect2 = fitz.Rect(page_width - 70, 20, page_width - 20, 70)
            logger.info(f"Adding green square on page {page_idx + 1} at position {rect2}")
            annot2 = page.add_rect_annot(rect2)
            annot2.set_colors(stroke=(0, 1, 0))  # Green
            annot2.set_border(width=2)
            annot2.update()
            
            # Bottom-left corner - blue
            rect3 = fitz.Rect(20, page_height - 70, 70, page_height - 20)
            logger.info(f"Adding blue square on page {page_idx + 1} at position {rect3}")
            annot3 = page.add_rect_annot(rect3)
            annot3.set_colors(stroke=(0, 0, 1))  # Blue
            annot3.set_border(width=2)
            annot3.update()
            
            # Bottom-right corner - yellow
            rect4 = fitz.Rect(page_width - 70, page_height - 70, page_width - 20, page_height - 20)
            logger.info(f"Adding yellow square on page {page_idx + 1} at position {rect4}")
            annot4 = page.add_rect_annot(rect4)
            annot4.set_colors(stroke=(1, 1, 0))  # Yellow
            annot4.set_border(width=2)
            annot4.update()
            
            # Center - purple
            center_x = page_width / 2
            center_y = page_height / 2
            rect5 = fitz.Rect(center_x - 25, center_y - 25, center_x + 25, center_y + 25)
            logger.info(f"Adding purple square on page {page_idx + 1} at position {rect5}")
            annot5 = page.add_rect_annot(rect5)
            annot5.set_colors(stroke=(1, 0, 1))  # Purple
            annot5.set_border(width=3)
            annot5.update()
            
            logger.info(f"Added test rectangles to page {page_idx + 1}")
        
        # Save the test PDF
        logger.info(f"Saving test PDF to: {test_pdf_path}")
        doc.save(test_pdf_path)
        doc.close()
        
        logger.info(f"Test PDF saved at: {test_pdf_path}")
        
    except Exception as e:
        logger.exception(f"Error creating test PDF: {e}")

if __name__ == "__main__":
    main() 