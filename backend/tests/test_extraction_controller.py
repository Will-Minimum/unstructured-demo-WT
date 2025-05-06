import unittest
from unittest.mock import patch, MagicMock
import json
from flask import Flask

from controllers.extraction_controller import extraction_bp, uploaded_files

class TestExtractionController(unittest.TestCase):
    """Tests for the Extraction Controller."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.app.register_blueprint(extraction_bp, url_prefix='/api')
        self.client = self.app.test_client()
        # Reset uploaded files dict
        uploaded_files.clear()
        # Add a test file to uploaded_files
        uploaded_files['test_file_id'] = {
            "path": "/path/to/test.pdf",
            "filename": "test.pdf"
        }
    
    def test_upload_file_no_file(self):
        """Test upload endpoint when no file is provided."""
        response = self.client.post('/api/upload')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'No file uploaded')
    
    @patch('controllers.extraction_controller.pdf_service.process_pdf')
    @patch('controllers.extraction_controller.schema_service.get_schema_by_id')
    def test_extract_information_pdf_processing_error(self, mock_get_schema, mock_process_pdf):
        """Test extraction endpoint when PDF processing fails."""
        # Set up mocks
        mock_schema = MagicMock()
        mock_schema.id = 'test_schema'
        mock_get_schema.return_value = mock_schema
        
        # Simulate PDF processing failure
        mock_process_pdf.return_value = None
        
        # Make the request
        request_data = {
            'file_id': 'test_file_id',
            'schema_id': 'test_schema'
        }
        response = self.client.post('/api/extract', 
                                  json=request_data, 
                                  content_type='application/json')
        
        # Check the response
        self.assertEqual(response.status_code, 500)
        data = json.loads(response.data)
        self.assertEqual(data['error'], 'PDF processing failed')
    
    @patch('controllers.extraction_controller.pdf_service.process_pdf')
    @patch('controllers.extraction_controller.pdf_service.extract_coordinates')
    @patch('controllers.extraction_controller.pdf_service.map_extracted_fields_to_locations')
    @patch('controllers.extraction_controller.llm_service.extract_information')
    @patch('controllers.extraction_controller.schema_service.get_schema_by_id')
    def test_extract_information_success(self, mock_get_schema, mock_extract_info, 
                                       mock_map_locations, mock_extract_coords, 
                                       mock_process_pdf):
        """Test successful extraction."""
        # Set up mocks
        mock_schema = MagicMock()
        mock_schema.id = 'test_schema'
        mock_get_schema.return_value = mock_schema
        
        mock_process_pdf.return_value = [{"text": "Sample text"}]
        mock_extract_coords.return_value = [{"text": "Sample text", "page_number": 1}]
        mock_extract_info.return_value = {"extracted_data": {"field1": "value1"}}
        mock_map_locations.return_value = {"field1": [{"page_number": 1}]}
        
        # Make the request
        request_data = {
            'file_id': 'test_file_id',
            'schema_id': 'test_schema'
        }
        response = self.client.post('/api/extract', 
                                  json=request_data, 
                                  content_type='application/json')
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('extraction_id', data)
        self.assertEqual(data['extracted_data'], {"field1": "value1"})
        self.assertEqual(data['source_locations'], {"field1": [{"page_number": 1}]})

if __name__ == '__main__':
    unittest.main() 