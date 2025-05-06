import os
import uuid
import tempfile
from typing import Dict, List, Any, Tuple
import json
import requests
import sys
import traceback
import logging
import time
from werkzeug.utils import secure_filename

from unstructured_client import UnstructuredClient
from unstructured_client.models import shared
from unstructured_client.models import operations
from PIL import Image
import numpy as np

from config import Config

# Create a logger for this module
logger = logging.getLogger(__name__)

class PDFService:
    """Service for processing PDF documents using Unstructured API."""
    
    def __init__(self):
        """Initialize the PDF service."""
        logger.info("Initializing PDFService")
        
        self.upload_folder = Config.UPLOAD_FOLDER
        self.api_key = os.environ.get("UNSTRUCTURED_API_KEY")
        self.unstructured_api_url = Config.UNSTRUCTURED_API_URL
        logger.info(f"Unstructured API URL: {self.unstructured_api_url}")
        
        if not self.api_key:
            logger.warning("UNSTRUCTURED_API_KEY environment variable is not set, API calls will likely fail")
        else:
            # Test the API key to make sure it's valid
            key_valid = self._validate_api_key()
            if key_valid:
                logger.info("✅ Unstructured API key is valid!")
            else:
                logger.error("❌ Unstructured API key validation failed. API calls will likely fail.")
        
        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def _validate_api_key(self) -> bool:
        """Validate the Unstructured API key by making a test request.
        
        Returns:
            bool: True if the API key is valid, False otherwise
        """
        try:
            logger.info("Testing Unstructured API key with a simple request...")
            
            # Create a simple request to validate the API key
            # Use the healthcheck endpoint if available, or a minimal request
            session = requests.Session()
            headers = {
                "accept": "application/json",
                "unstructured-api-key": self.api_key
            }
            
            # Try a simple GET to check authentication
            response = session.get(
                f"{self.unstructured_api_url}/general/v0/elements/validate",
                headers=headers,
                timeout=10  # Short timeout for key validation
            )
            
            if response.status_code == 401:
                logger.error(f"API key validation failed: {response.text}")
                return False
            elif response.status_code in (200, 404):  # 404 is acceptable - just means endpoint doesn't exist, but auth worked
                # If we get 200 or 404, the key is probably valid (not 401 unauthorized)
                logger.info(f"API key validation succeeded with status code {response.status_code}")
                return True
            else:
                logger.warning(f"API key validation returned unexpected status code: {response.status_code}")
                logger.warning(f"Response: {response.text}")
                # Assume it might work for actual requests
                return True
                
        except requests.exceptions.Timeout:
            logger.warning("API key validation timed out")
            return False
        except requests.exceptions.ConnectionError as ce:
            logger.warning(f"Connection error during API key validation: {ce}")
            return False
        except Exception as e:
            logger.exception(f"Error validating API key: {e}")
            return False
    
    def save_uploaded_file(self, file) -> Tuple[str, str]:
        """Save an uploaded file and return its ID and path.
        
        Args:
            file: The uploaded file object
            
        Returns:
            Tuple of (file_id, file_path)
        """
        logger.info(f"Saving uploaded file: {file.filename}")
        
        # Generate a secure filename
        secure_name = secure_filename(file.filename)
        
        # Generate a unique ID for the file
        file_id = str(uuid.uuid4())
        
        # Create the filename with the ID
        filename = f"{file_id}_{secure_name}"
        
        # Create the full path
        file_path = os.path.join(self.upload_folder, filename)
        
        # Save the file
        file.save(file_path)
        logger.info(f"File saved at: {file_path}")
        
        return file_id, file_path
    
    def process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a PDF using Unstructured API.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of extracted elements with text and coordinates
        """
        logger.info(f"Processing PDF: {file_path}")
        
        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None
            
            # Check if API key is available
            if not self.api_key:
                logger.error("UNSTRUCTURED_API_KEY is not set. Cannot process PDF without authentication.")
                return None
                
            # Create the API request
            logger.info(f"Preparing API request to Unstructured API: {self.unstructured_api_url}")
            start_time = time.time()
            
            # Create the client
            client = UnstructuredClient(
                api_key_auth=self.api_key,
                server_url=self.unstructured_api_url
            )
            
            # Read the file and prepare request
            with open(file_path, 'rb') as f:
                file_content = f.read()
                
                # Log file size to help diagnose potential timeout issues
                file_size_mb = len(file_content) / (1024 * 1024)
                logger.info(f"Sending PDF file of size: {file_size_mb:.2f} MB to Unstructured API")
                
                # Create the request structure
                req = {
                    "partition_parameters": {
                        "files": {
                            "content": file_content,
                            "file_name": os.path.basename(file_path),
                        },
                        "strategy": shared.Strategy.HI_RES,
                        "coordinates": True,
                        "split_pdf_page": True,
                        "split_pdf_allow_failed": True,
                        "split_pdf_concurrency_level": 15
                    }
                }
                
                try:
                    logger.info("Sending request to Unstructured API - this may take some time for large documents...")
                    
                    # Use a longer timeout for larger files
                    timeout = max(60, min(300, int(file_size_mb * 10)))  # 10 seconds per MB, between 60-300 seconds
                    logger.info(f"Using timeout of {timeout} seconds for this request")
                    
                    # Make the synchronous API call
                    response = client.general.partition(
                        request=req
                    )
                    
                    # Convert elements to list of dictionaries
                    elements = [element for element in response.elements]
                    
                    processing_time = time.time() - start_time
                    logger.info(f"PDF processed in {processing_time:.2f} seconds, received {len(elements)} elements")
                    
                    # Log element types
                    element_types = {}
                    for element in elements:
                        element_type = element["type"]
                        element_types[element_type] = element_types.get(element_type, 0) + 1
                    
                    logger.info(f"Element types found: {json.dumps(element_types, indent=2)}")
                    
                    return elements
                    
                except Exception as e:
                    logger.exception(f"Error calling Unstructured API: {e}")
                    logger.error(f"Stack trace: {traceback.format_exc()}")
                    return None
                    
        except Exception as e:
            logger.exception(f"Error processing PDF: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return None
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract all text from a PDF using Unstructured API.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text as a string
        """
        try:
            elements = self.process_pdf(file_path)
            if elements is None:
                logger.error("Failed to extract text: PDF processing returned None")
                return ""
                
            return "\n\n".join([element["text"] for element in elements if element["text"].strip()])
        except Exception as e:
            logger.exception(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_coordinates(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract coordinates from elements.
        
        Args:
            elements: List of elements with coordinate information
            
        Returns:
            List of elements with properly formatted coordinates.
            Note: Coordinates are in top-left origin system where y increases downward.
        """
        logger.info(f"Extracting coordinates from {len(elements)} elements")
        
        elements_with_coords = []
        missing_coords = 0
        
        for element in elements:
            # Skip elements without metadata
            if "metadata" not in element:
                logger.debug(f"Element missing metadata: {element}")
                missing_coords += 1
                continue
            
            # Check for coordinates in metadata
            metadata = element["metadata"]
            
            # First try the standard coordinates key
            if "coordinates" in metadata and metadata["coordinates"]:
                coordinates = metadata["coordinates"]
                logger.debug(f"Coordinates format: {json.dumps(coordinates, indent=2)}")
                
                # Extract page number and bounding box
                page_number = coordinates.get("page_number", metadata.get("page_number", 1))
                
                # Handle different formats of coordinates
                if "points" in coordinates and isinstance(coordinates["points"], list) and len(coordinates["points"]) >= 4:
                    points = coordinates["points"]
                    # Points are in format [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
                    # Where points start from top-left and go counter-clockwise
                    bounding_box = {
                        "x0": min(p[0] for p in points),  # leftmost x
                        "y0": min(p[1] for p in points),  # topmost y
                        "x1": max(p[0] for p in points),  # rightmost x
                        "y1": max(p[1] for p in points)   # bottommost y
                    }
                elif all(k in coordinates for k in ["x0", "y0", "x1", "y1"]):
                    # Format with direct bounding box coordinates
                    # Already in top-left origin system
                    bounding_box = {
                        "x0": coordinates["x0"],
                        "y0": coordinates["y0"],
                        "x1": coordinates["x1"],
                        "y1": coordinates["y1"]
                    }
                else:
                    logger.debug(f"Element has coordinates but in an unexpected format: {coordinates}")
                    missing_coords += 1
                    continue
                
                # Create a new element with coordinates
                element_with_coords = {
                    "text": element["text"],
                    "type": element["type"],
                    "page_number": page_number,
                    "bounding_box": bounding_box,
                    "coordinate_system": "top-left-origin"  # Document the coordinate system
                }
                
                elements_with_coords.append(element_with_coords)
            
            # Try alternative formats - some versions might have coordinates directly in metadata
            elif all(k in metadata for k in ["x0", "y0", "x1", "y1"]):
                page_number = metadata.get("page_number", 1)
                
                bounding_box = {
                    "x0": metadata["x0"],
                    "y0": metadata["y0"],
                    "x1": metadata["x1"],
                    "y1": metadata["y1"]
                }
                
                element_with_coords = {
                    "text": element["text"],
                    "type": element["type"],
                    "page_number": page_number,
                    "bounding_box": bounding_box
                }
                
                elements_with_coords.append(element_with_coords)
            else:
                logger.debug(f"Element missing coordinates in metadata: {element}")
                missing_coords += 1
        
        logger.info(f"Extracted coordinates for {len(elements_with_coords)} elements (missing: {missing_coords})")
        
        # Log a sample element with coordinates if available
        if elements_with_coords:
            logger.debug(f"Sample element with coordinates: {json.dumps(elements_with_coords[0], indent=2)}")
        
        return elements_with_coords
    
    def convert_pdf_to_images(self, file_path: str) -> List[str]:
        """Convert PDF pages to images.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of paths to the generated images
        """
        try:
            print(f"Converting PDF to images: {file_path}")
            from pdf2image import convert_from_path
            
            # Create a directory for the images
            file_id = os.path.basename(file_path).split('.')[0]
            images_dir = os.path.join(self.upload_folder, f"{file_id}_images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=300)
            image_paths = []
            
            # Save images
            for i, image in enumerate(images):
                image_path = os.path.join(images_dir, f"page_{i + 1}.png")
                image.save(image_path, "PNG")
                image_paths.append(image_path)
            
            print(f"Successfully converted PDF to {len(image_paths)} images")
            return image_paths
            
        except ImportError as import_error:
            print(f"ImportError: {import_error}")
            print("Warning: pdf2image not installed. Using fallback method.")
            
            try:
                # Fallback to create placeholder image paths using Unstructured API
                print("Getting number of pages using Unstructured API...")
                
                # Get the number of pages using Unstructured API
                client = UnstructuredClient(
                    api_key_auth=self.api_key
                )
                
                # Read file content
                with open(file_path, "rb") as f:
                    file_content = f.read()
                
                print(f"File size: {len(file_content)} bytes")
                
                # Create files parameter
                files = shared.Files(
                    content=file_content,
                    file_name=os.path.basename(file_path)
                )
                
                # Create partition parameters
                partition_params = shared.PartitionParameters(
                    files=files,
                    strategy="hi_res",
                    coordinates=True
                )
                
                # Create partition request
                request = operations.PartitionRequest(
                    partition_parameters=partition_params
                )
                
                # Call the partition API
                print("Calling Unstructured API...")
                response = client.general.partition(request=request)
                
                # Debug: Print response structure for debugging
                print(f"Response type: {type(response)}")
                print(f"Response attributes: {dir(response)}")
                
                # Safely get the number of pages
                num_pages = 1
                if hasattr(response, 'elements'):
                    elements_data = response.elements
                    # Try to get page numbers from elements
                    page_numbers = []
                    for elem in elements_data:
                        try:
                            if isinstance(elem, dict) and 'metadata' in elem and isinstance(elem['metadata'], dict):
                                page_num = elem['metadata'].get('page_number', 1)
                                page_numbers.append(page_num)
                            elif hasattr(elem, 'metadata') and hasattr(elem.metadata, 'page_number'):
                                page_num = elem.metadata.page_number
                                page_numbers.append(page_num)
                        except Exception as e:
                            print(f"Error getting page number from element: {e}")
                            continue
                    
                    # Get max page number if any were found
                    if page_numbers:
                        num_pages = max(page_numbers)
                
                print(f"Detected {num_pages} pages in the PDF")
                
                # Create a directory for the images
                file_id = os.path.basename(file_path).split('.')[0]
                images_dir = os.path.join(self.upload_folder, f"{file_id}_images")
                os.makedirs(images_dir, exist_ok=True)
                
                # Create placeholder image paths
                image_paths = []
                for page_num in range(num_pages):
                    image_path = os.path.join(images_dir, f"page_{page_num + 1}.png")
                    image_paths.append(image_path)
                
                print(f"Created {len(image_paths)} placeholder image paths")
                return image_paths
                
            except Exception as api_error:
                print(f"Error using Unstructured API for page detection: {api_error}")
                print(f"Traceback: {traceback.format_exc()}")
                
                # Last resort: create a single placeholder image path
                file_id = os.path.basename(file_path).split('.')[0]
                images_dir = os.path.join(self.upload_folder, f"{file_id}_images")
                os.makedirs(images_dir, exist_ok=True)
                image_path = os.path.join(images_dir, "page_1.png")
                
                print(f"Created single fallback image path: {image_path}")
                return [image_path]
                
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            raise
    
    def map_extracted_fields_to_locations(self, extracted_data: Dict[str, Any], elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Map extracted field values to their source locations in the PDF.
        
        Args:
            extracted_data: Dictionary of extracted field values
            elements: List of elements with text and page numbers
            
        Returns:
            Dictionary of field locations with field names as keys
        """
        logger.info(f"Mapping extracted fields to locations, with {len(elements)} elements available")
        
        # Create a dictionary to store source locations for each field
        source_locations = {}
        
        # Track matches for debugging
        matches_found = 0
        fields_processed = 0
        
        # Process each field in the extracted data
        for field_name, field_info in extracted_data.items():
            fields_processed += 1
            logger.info(f"Processing field: {field_name}")
            
            # Skip empty fields
            if not field_info or not field_info.get("value"):
                logger.debug(f"Field {field_name} is empty, skipping")
                continue
            
            field_value = field_info["value"]
            source_text = field_info["source_text"]
            
            # Convert to string for comparison
            if not isinstance(field_value, str):
                field_value = str(field_value)
            
            # Find elements containing this field value
            matched_elements = []
            
            # Try different approaches to find matches
            exact_matches = []
            partial_matches = []
            
            for element in elements:
                element_text = element["text"].strip()
                
                # Skip elements with suspiciously large bounding boxes
                box_width = element["bounding_box"]["x1"] - element["bounding_box"]["x0"]
                box_height = element["bounding_box"]["y1"] - element["bounding_box"]["y0"]
                if box_width > 500 or box_height > 200:  # Typical text field shouldn't be larger than this
                    logger.debug(f"Skipping oversized element: {box_width}x{box_height}")
                    continue
                
                # Check for exact match with source text
                if source_text.lower().strip() == element_text.lower():
                    logger.debug(f"Found exact match for {field_name} source text in element text")
                    exact_matches.append(element)
                # Check for exact match with value
                elif field_value.lower().strip() == element_text.lower():
                    logger.debug(f"Found exact match for {field_name} value in element text")
                    exact_matches.append(element)
                # Check for partial match with source text, but only if the length difference is small
                elif (source_text.lower().strip() in element_text.lower() and 
                      len(element_text) <= len(source_text) * 1.5):  # Allow only 50% more text
                    logger.debug(f"Found partial match for {field_name} source text in element text")
                    partial_matches.append(element)
                # Check for partial match with value, but only if the length difference is small
                elif (field_value.lower().strip() in element_text.lower() and 
                      len(element_text) <= len(field_value) * 1.5):  # Allow only 50% more text
                    logger.debug(f"Found partial match for {field_name} value in element text")
                    partial_matches.append(element)
            
            # Prioritize exact matches, fall back to partial matches
            if exact_matches:
                matched_elements = exact_matches
                logger.info(f"Using {len(matched_elements)} exact matches for {field_name}")
            elif partial_matches:
                matched_elements = partial_matches
                logger.info(f"Using {len(matched_elements)} partial matches for {field_name}")
            else:
                logger.warning(f"No matches found for field {field_name}")
                continue
            
            # Store the location data for this field
            field_locations = []
            
            for element in matched_elements:
                location = {
                    "page_number": element["page_number"],
                    "bounding_box": {
                        "x0": element["bounding_box"]["x0"],
                        "y0": element["bounding_box"]["y0"],
                        "x1": element["bounding_box"]["x1"],
                        "y1": element["bounding_box"]["y1"]
                    }
                }
                field_locations.append(location)
                matches_found += 1
            
            # Store the locations for this field
            if field_locations:
                source_locations[field_name] = field_locations
                logger.info(f"Added {len(field_locations)} source locations for field {field_name}")
                logger.debug(f"Source locations for {field_name}: {json.dumps(field_locations, indent=2)}")
        
        logger.info(f"Mapping completed: {matches_found} matches found for {fields_processed} processed fields")
        logger.info(f"Final source_locations: {json.dumps(source_locations, indent=2)}")
        
        # Return the source locations dictionary
        return source_locations
    
    def create_annotated_pdf(self, original_pdf_path: str, source_locations: Dict[str, List[Dict[str, Any]]], 
                              active_field: str = None) -> str:
        """Create a new PDF with bounding boxes drawn directly on it.
        
        Args:
            original_pdf_path: Path to the original PDF file
            source_locations: Dictionary of field locations with field names as keys
            active_field: Optional name of the field to highlight (if None, show all)
            
        Returns:
            Path to the annotated PDF file
        """
        logger.info(f"Creating annotated PDF from {original_pdf_path}")
        
        try:
            import fitz  # PyMuPDF
            from datetime import datetime
            
            # Create a unique filename for the annotated PDF
            file_id = os.path.basename(original_pdf_path).split('.')[0]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            annotated_pdf_path = os.path.join(self.upload_folder, f"{file_id}_annotated_{timestamp}.pdf")
            
            # Open the original PDF
            doc = fitz.open(original_pdf_path)
            
            # Color mapping for different fields (in RGB format, values from 0 to 1)
            colors = {
                "account_number": (1, 0, 0),  # Red
                "meter_number": (0, 1, 0),    # Green
                "supplier_name": (0, 0, 1),   # Blue
                "rate_plan": (1, 0.5, 0),     # Orange
                "address_of_consuming_site": (0.5, 0, 0.5),  # Purple
                "total_amount_due": (1, 1, 0),  # Yellow
                "payment_due_date": (0, 0.5, 0.5),  # Teal
                "start_date_of_consumption": (0.5, 0.5, 0),  # Olive
                "end_date_of_consumption": (0, 1, 1),  # Cyan
                "consumption_amount": (0.5, 0, 0),  # Maroon
                "consumption_unit": (0, 0.5, 0),  # Dark Green
                "peak_consumption": (0.7, 0, 0.7),  # Purple
                "off_peak_consumption": (0.7, 0.7, 0)  # Dark Yellow
            }
            
            # Default for unknown fields
            default_color = (0.5, 0.5, 0.5)  # Gray
            
            # Create a list of fields to process
            fields_to_process = [active_field] if active_field else source_locations.keys()
            
            for field_name in fields_to_process:
                if field_name not in source_locations:
                    logger.warning(f"Field {field_name} not in source_locations, skipping")
                    continue
                
                # Get color for this field
                rgb = colors.get(field_name, default_color)
                # No conversion needed - PyMuPDF expects colors in 0-1 range
                stroke_color = rgb
                
                # Process each location for this field
                for location in source_locations[field_name]:
                    page_number = location["page_number"] - 1  # 0-based indexing
                    bbox = location["bounding_box"]
                    
                    # Skip if page number is out of range
                    if page_number < 0 or page_number >= len(doc):
                        logger.warning(f"Page number {page_number + 1} out of range, skipping")
                        continue
                    
                    # Get the page
                    page = doc[page_number]
                    
                    # Create rectangle for the bounding box
                    rect = fitz.Rect(bbox["x0"], bbox["y0"], bbox["x1"], bbox["y1"])
                    
                    try:
                        # Add rectangle annotation - updated to use correct parameters
                        annot = page.add_rect_annot(rect)
                        annot.set_colors(stroke=stroke_color)
                        annot.set_border(width=1.5)  # Set line width
                        annot.update()
                        
                        # Add text annotation with the field name
                        text_point = fitz.Point(bbox["x0"], bbox["y0"] - 10)
                        text_annot = page.add_text_annot(text_point, field_name)
                        text_annot.update()
                        
                        logger.debug(f"Added annotation for field {field_name} on page {page_number + 1}")
                    except Exception as e:
                        logger.exception(f"Error adding annotation: {e}")
                        continue
            
            # Save the annotated PDF
            doc.save(annotated_pdf_path)
            doc.close()
            
            logger.info(f"Annotated PDF saved at: {annotated_pdf_path}")
            return annotated_pdf_path
            
        except ImportError:
            logger.error("PyMuPDF (fitz) not installed. Please install with: pip install pymupdf")
            return original_pdf_path
        except Exception as e:
            logger.exception(f"Error creating annotated PDF: {e}")
            return original_pdf_path


# Create a singleton instance
pdf_service = PDFService()
