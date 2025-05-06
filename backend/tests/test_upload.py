import os
import unittest
import tempfile
from io import BytesIO
import sys
import json
from unittest.mock import patch

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from config import Config
from services.pdf_service import PDFService

class UploadTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Create a temporary directory for uploads
        self.test_upload_dir = tempfile.mkdtemp()
        
        # Patch the save_uploaded_file method to use our test directory
        self.patcher = patch.object(PDFService, 'save_uploaded_file')
        self.mock_save = self.patcher.start()
        self.mock_save.return_value = ('test-file-id', os.path.join(self.test_upload_dir, 'test-file-id_test.pdf'))

    def tearDown(self):
        # Stop the patcher
        self.patcher.stop()
        
        # Clean up the temporary directory
        for filename in os.listdir(self.test_upload_dir):
            os.remove(os.path.join(self.test_upload_dir, filename))
        os.rmdir(self.test_upload_dir)

    def test_upload_pdf(self):
        """Test uploading a PDF file"""
        # Create a test PDF file
        test_pdf = BytesIO(b'%PDF-1.4\nThis is a test PDF file')
        
        # Write the test file to the test directory
        with open(os.path.join(self.test_upload_dir, 'test-file-id_test.pdf'), 'wb') as f:
            f.write(test_pdf.getvalue())
        
        # Send a POST request to the upload endpoint
        response = self.app.post(
            '/api/upload',
            data={
                'file': (BytesIO(b'%PDF-1.4\nThis is a test PDF file'), 'test.pdf')
            },
            content_type='multipart/form-data'
        )
        
        # Check the response
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('file_id', json_data)
        self.assertEqual(json_data['filename'], 'test.pdf')
        
        # Check that the file exists in the test directory
        self.assertTrue(os.path.exists(os.path.join(self.test_upload_dir, 'test-file-id_test.pdf')))
        
    def test_upload_non_pdf(self):
        """Test uploading a non-PDF file"""
        # Create a test text file
        test_file = BytesIO(b'This is a test text file')
        
        # Send a POST request to the upload endpoint
        response = self.app.post(
            '/api/upload',
            data={
                'file': (test_file, 'test.txt')
            },
            content_type='multipart/form-data'
        )
        
        # Check the response - should be an error
        self.assertEqual(response.status_code, 415)
        json_data = response.get_json()
        self.assertIn('error', json_data)
        
    def test_upload_no_file(self):
        """Test uploading with no file"""
        # Send a POST request to the upload endpoint with no file
        response = self.app.post(
            '/api/upload',
            data={},
            content_type='multipart/form-data'
        )
        
        # Check the response - should be an error
        self.assertEqual(response.status_code, 400)
        json_data = response.get_json()
        self.assertIn('error', json_data)

if __name__ == '__main__':
    unittest.main() 