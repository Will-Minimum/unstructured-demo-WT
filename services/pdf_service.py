import os
import uuid
import tempfile
from typing import Dict, List, Any, Tuple
import json
import requests

import PyPDF2
from PIL import Image
import numpy as np

from config import Config

class PDFService:
    """Service for processing PDF documents using Unstructured API."""
    
    def __init__(self):
        """Initialize the PDF service."""
        self.api_key = Config.UNSTRUCTURED_API_KEY
        self.upload_folder = Config.UPLOAD_FOLDER
        
        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def save_uploaded_file(self, file) -> Tuple[str, str]:
        """Save an uploaded file and return its ID and path.
        
        Args:
            file: The uploaded file object
            
        Returns:
            Tuple of (file_id, file_path)
        """
        file_id = str(uuid.uuid4())
        filename = file.filename
        file_path = os.path.join(self.upload_folder, f"{file_id}_{filename}")
        
        file.save(file_path)
        
        return file_id, file_path
    
    def process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a PDF using Unstructured API.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of extracted elements with text and coordinates
        """
        try:
            # For demo purposes, we'll extract text using PyPDF2 instead of Unstructured API
            elements = []
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                
                for page_num in range(num_pages):
                    page = reader.pages[page_num]
                    text = page.extract_text()
                    
                    # Split text into paragraphs
                    paragraphs = text.split('\n\n')
                    
                    for i, paragraph in enumerate(paragraphs):
                        if paragraph.strip():
                            # Create a mock element with coordinates
                            element_dict = {
                                "type": "Text",
                                "text": paragraph,
                                "page_number": page_num + 1,
                                "coordinates": {
                                    "x0": 0.1,
                                    "y0": 0.1 + (i * 0.1),
                                    "x1": 0.9,
                                    "y1": 0.1 + ((i + 1) * 0.1),
                                }
                            }
                            
                            elements.append(element_dict)
            
            return elements
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            raise
    
    def extract_coordinates(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract bounding box coordinates from elements.
        
        Args:
            elements: List of elements from Unstructured API
            
        Returns:
            List of elements with normalized bounding box coordinates
        """
        result = []
        
        for element in elements:
            if "coordinates" in element:
                # Normalize coordinates to 0-100 range (percentage of page)
                coords = element["coordinates"]
                bbox = [
                    coords["x0"] * 100,
                    coords["y0"] * 100,
                    coords["x1"] * 100,
                    coords["y1"] * 100
                ]
                
                result.append({
                    "text": element["text"],
                    "page": element["page_number"],
                    "bbox": bbox,
                    "type": element["type"]
                })
        
        return result
    
    def convert_pdf_to_images(self, file_path: str) -> List[str]:
        """Convert PDF pages to images.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of paths to the generated images
        """
        image_paths = []
        
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                num_pages = len(reader.pages)
                
                # Create a directory for the images
                file_id = os.path.basename(file_path).split('_')[0]
                images_dir = os.path.join(self.upload_folder, f"{file_id}_images")
                os.makedirs(images_dir, exist_ok=True)
                
                # Convert each page to an image
                for page_num in range(num_pages):
                    # This is a placeholder - in a real implementation, you would use
                    # a library like pdf2image or a similar approach to convert PDF pages to images
                    image_path = os.path.join(images_dir, f"page_{page_num + 1}.png")
                    image_paths.append(image_path)
                    
                    # Placeholder for actual conversion
                    # with open(image_path, 'w') as img_file:
                    #     img_file.write("Placeholder for PDF image")
            
            return image_paths
            
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            raise
    
    def map_extracted_fields_to_locations(self, extracted_data: Dict[str, Any], elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Map extracted field values to their source locations in the PDF.
        
        Args:
            extracted_data: Dictionary of extracted field values
            elements: List of elements with text and coordinates
            
        Returns:
            List of field locations with page numbers and bounding boxes
        """
        source_locations = []
        
        for field_name, field_value in extracted_data.items():
            if not field_value:
                continue
                
            # Find elements that contain the field value
            matching_elements = []
            for element in elements:
                if field_value in element["text"]:
                    matching_elements.append(element)
            
            # If we found matching elements, use the first one
            if matching_elements:
                element = matching_elements[0]
                source_locations.append({
                    "field": field_name,
                    "page": element["page"],
                    "bbox": element["bbox"]
                })
        
        return source_locations


# Create a singleton instance
pdf_service = PDFService() 