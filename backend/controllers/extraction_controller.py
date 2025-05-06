import os
import uuid
import logging
import json
from flask import Blueprint, request, jsonify, current_app, send_from_directory
import werkzeug
from services.pdf_service import pdf_service
from services.llm_service import llm_service
from services.schema_service import schema_service
from services.extraction_service import extraction_service
import asyncio
import traceback

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a blueprint for extraction routes
extraction_bp = Blueprint('extraction', __name__)

# Store uploaded files and their processing results
uploaded_files = {}
extraction_results = {}

@extraction_bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    logger.info("=== UPLOAD FILE ENDPOINT CALLED ===")
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'File must be a PDF'}), 400
    
    logger.info(f"Uploading file: {file.filename}")
    
    # Save the file and get its ID
    file_id, file_path = pdf_service.save_uploaded_file(file)
    logger.info(f"File saved with ID: {file_id} at path: {file_path}")
    
    # Store the file information
    uploaded_files[file_id] = {
        "filename": file.filename,
        "path": file_path
    }
    logger.info(f"File information stored in uploaded_files dictionary: {uploaded_files[file_id]}")
    
    return jsonify({
        'file_id': file_id,
        'filename': file.filename
    })

@extraction_bp.route('/schemas', methods=['GET'])
def get_schemas():
    """Return a list of available extraction schemas."""
    logger.info("=== GET SCHEMAS ENDPOINT CALLED ===")
    
    try:
        schemas = schema_service.get_all_schemas()
        logger.info(f"Returning {len(schemas)} schemas")
        return jsonify({"schemas": schemas}), 200
        
    except Exception as e:
        logger.exception(f"Error getting schemas: {e}")
        return jsonify({"error": "Failed to retrieve schemas"}), 500


@extraction_bp.route('/schemas/<schema_id>', methods=['GET'])
def get_schema_details(schema_id):
    """Return details of a specific schema."""
    logger.info(f"=== GET SCHEMA DETAILS ENDPOINT CALLED FOR SCHEMA: {schema_id} ===")
    
    try:
        schema = schema_service.get_schema_by_id(schema_id)
        
        if not schema:
            logger.error(f"Schema not found: {schema_id}")
            return jsonify({"error": "Schema not found"}), 404
        
        logger.info(f"Returning details for schema: {schema.id}")
        return jsonify(schema.to_dict()), 200
        
    except Exception as e:
        logger.exception(f"Error getting schema details: {e}")
        return jsonify({"error": "Failed to retrieve schema details"}), 500

@extraction_bp.route('/extract', methods=['POST'])
def extract_information():
    """Extract information from a PDF using a schema."""
    logger.info("=== EXTRACT INFORMATION ENDPOINT CALLED ===")
    
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    file_id = data.get('file_id')
    schema_id = data.get('schema_id')
    
    if not file_id or not schema_id:
        return jsonify({'error': 'Missing file_id or schema_id'}), 400
    
    logger.info(f"Extraction requested for file_id: {file_id}, schema_id: {schema_id}")
    
    # Get the schema
    schema = schema_service.get_schema_by_id(schema_id)
    if not schema:
        return jsonify({'error': f'Schema not found: {schema_id}'}), 404
    
    # Find the file
    file_path = None
    for filename in os.listdir(pdf_service.upload_folder):
        if filename.startswith(file_id):
            file_path = os.path.join(pdf_service.upload_folder, filename)
            break
    
    if not file_path:
        return jsonify({'error': f'File not found for ID: {file_id}'}), 404
    
    logger.info(f"Processing file: {file_path}")
    
    # Process the PDF with Unstructured API
    logger.info("Calling Unstructured API to process PDF")
    elements = pdf_service.process_pdf(file_path)
    
    if elements is None:
        logger.error("PDF processing failed with the Unstructured API")
        return jsonify({'error': 'Failed to process PDF'}), 500
    
    # Extract coordinates from elements
    logger.info("Extracting coordinates from elements")
    elements_with_coords = pdf_service.extract_coordinates(elements)
    logger.info(f"Extracted coordinates for {len(elements_with_coords)} elements")
    
    # Extract information using the schema
    logger.info("Extracting information using schema")
    extracted_data = extraction_service.extract_information(elements, schema)
    
    if extracted_data is None:
        logger.error("Failed to extract information from PDF")
        return jsonify({'error': 'Failed to extract information from PDF'}), 500
    
    # Map extracted fields to their locations in the PDF
    logger.info("Mapping extracted fields to their locations in the PDF")
    source_locations = pdf_service.map_extracted_fields_to_locations(extracted_data, elements_with_coords)
    
    # Log the source locations type and content for debugging
    logger.info(f"Source locations type: {type(source_locations)}")
    logger.info(f"Source locations: {source_locations}")
    
    # Create a unique ID for this extraction
    extraction_id = os.urandom(16).hex()
    
    # Store the extraction results for this file ID
    extraction_results[file_id] = {
        "extraction_id": extraction_id,
        "extracted_data": extracted_data,
        "source_locations": source_locations
    }
    logger.info(f"Stored extraction results for file ID: {file_id}")
    
    logger.info("Sending response with source_locations")
    
    return jsonify({
        'extraction_id': extraction_id,
        'extracted_data': extracted_data,
        'source_locations': source_locations
    })

@extraction_bp.route('/pdf/<file_id>', methods=['GET'])
def get_pdf(file_id):
    """Return the PDF file for viewing."""
    logger.info(f"=== GET PDF ENDPOINT CALLED FOR FILE: {file_id} ===")
    
    # Check if the file exists
    if file_id not in uploaded_files:
        logger.error(f"File not found: {file_id}")
        return jsonify({"error": "File not found"}), 404
    
    try:
        # Get the file path
        file_path = uploaded_files[file_id]["path"]
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        
        logger.info(f"Returning PDF file: {filename} from directory: {directory}")
        return send_from_directory(directory, filename, as_attachment=False)
        
    except Exception as e:
        logger.exception(f"Error retrieving PDF: {e}")
        return jsonify({"error": "Failed to retrieve PDF"}), 500

@extraction_bp.route('/annotated-pdf', methods=['POST'])
def get_annotated_pdf():
    """Create and return a PDF with annotations for the extracted fields."""
    logger.info("=== GET ANNOTATED PDF ENDPOINT CALLED ===")
    
    try:
        # Get the request data
        data = request.json
        file_id = data.get('fileId')
        active_field = data.get('activeField')  # Optional field to highlight
        
        if not file_id:
            return jsonify({"error": "File ID is required"}), 400
        
        # Check if the file exists
        file_info = uploaded_files.get(file_id)
        if not file_info:
            return jsonify({"error": f"File with ID {file_id} not found"}), 404
        
        original_pdf_path = file_info["path"]
        
        # Get the source locations for this file from the extracted_data dictionary
        source_locations = extraction_results.get(file_id, {}).get("source_locations")
        if not source_locations:
            return jsonify({"error": "No source locations available for this file"}), 404
        
        # Create the annotated PDF
        annotated_pdf_path = pdf_service.create_annotated_pdf(
            original_pdf_path=original_pdf_path,
            source_locations=source_locations,
            active_field=active_field
        )
        
        # Get the file name
        annotated_file_name = os.path.basename(annotated_pdf_path)
        
        # Generate a new ID for the annotated PDF
        annotated_file_id = annotated_file_name.split('_')[0]
        
        # Store the annotated PDF in the uploaded_files dictionary
        uploaded_files[annotated_file_id] = {
            "filename": annotated_file_name,
            "path": annotated_pdf_path
        }
        
        logger.info(f"Annotated PDF created: {annotated_pdf_path}")
        
        # Return the ID of the annotated PDF
        return jsonify({
            "fileId": annotated_file_id,
            "status": "success"
        })
        
    except Exception as e:
        logger.exception(f"Error creating annotated PDF: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
