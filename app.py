#!/usr/bin/env python3
import os
import json
import uuid
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from extract import PDFExtractor

app = Flask(__name__, static_folder='frontend/build')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ANNOTATED_PDFS_FOLDER = 'annotated_pdfs'
SCHEMAS_FOLDER = 'schemas'
ALLOWED_EXTENSIONS = {'pdf'}

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)
os.makedirs(ANNOTATED_PDFS_FOLDER, exist_ok=True)
os.makedirs(SCHEMAS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max upload size

# Load schemas from the schemas directory
def load_schemas():
    schemas = []
    for filename in os.listdir(SCHEMAS_FOLDER):
        if filename.endswith('.json'):
            filepath = os.path.join(SCHEMAS_FOLDER, filename)
            try:
                with open(filepath, 'r') as f:
                    schema = json.load(f)
                    schema_id = os.path.splitext(filename)[0]
                    fields = [field['name'] for field in schema['fields']]
                    schemas.append({
                        "id": schema_id,
                        "name": schema["name"],
                        "fields": fields
                    })
            except Exception as e:
                print(f"Error loading schema {filename}: {e}")
    return schemas

# List of available schemas
SCHEMAS = load_schemas()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/schemas', methods=['GET'])
def get_schemas():
    return jsonify(SCHEMAS)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    # Check if file part is in the request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # Check if user selected a file
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Check if the file is allowed
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Get the schema ID from the request
    schema_id = request.form.get('schema')
    if not schema_id:
        return jsonify({'error': 'No schema specified'}), 400
    
    # Find the schema file path
    schema_path = os.path.join(SCHEMAS_FOLDER, f"{schema_id}.json")
    if not os.path.exists(schema_path):
        return jsonify({'error': 'Invalid schema'}), 400

    # Load the schema
    with open(schema_path, 'r') as f:
        schema_data = json.load(f)
    
    # Generate a unique filename to prevent collisions
    unique_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    base, ext = os.path.splitext(filename)
    unique_filename = f"{base}_{unique_id}{ext}"
    
    # Save the file
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    # Process the file using PDFExtractor
    try:
        extractor = PDFExtractor()
        # Process the PDF and get the elements
        elements = extractor.process_pdf(filepath)
        
        if not elements:
            return jsonify({'error': 'Failed to process PDF'}), 500
        
        # Extract information using the schema
        extracted_data = extractor.extract_information(elements, schema_data)
        
        if not extracted_data:
            return jsonify({'error': 'Failed to extract information from PDF'}), 500
            
        # Save the results
        results_path = os.path.join(RESULTS_FOLDER, f"results_{unique_id}.json")
        extractor.save_results(extracted_data, results_path)
        
        # Map extracted fields to locations in the document
        field_locations = extractor.map_extracted_fields_to_locations(extracted_data, elements)
        
        # Create an annotated PDF
        annotated_pdf_path = extractor.create_annotated_pdf(filepath, field_locations)
        
        # Generate response with extraction results and file paths
        response = {
            'id': unique_id,
            'original_filename': filename,
            'extracted_data': extracted_data,
            'annotated_pdf': os.path.basename(annotated_pdf_path),
            'schema': schema_data["name"]
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing document: {str(e)}'}), 500

@app.route('/api/results/<result_id>', methods=['GET'])
def get_result(result_id):
    results_path = os.path.join(RESULTS_FOLDER, f"results_{result_id}.json")
    
    if not os.path.exists(results_path):
        return jsonify({'error': 'Result not found'}), 404
        
    with open(results_path, 'r') as f:
        results = json.load(f)
        
    return jsonify(results), 200

@app.route('/api/pdf/<filename>', methods=['GET'])
def get_pdf(filename):
    return send_from_directory(ANNOTATED_PDFS_FOLDER, filename)

# Serve React frontend in production
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0') 