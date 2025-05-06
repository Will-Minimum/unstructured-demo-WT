import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
import requests

from services.pdf_service import pdf_service, PDFService

class TestPDFService(unittest.TestCase):
    """Tests for the PDF Service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_upload_dir = tempfile.mkdtemp()
        self.original_upload_folder = pdf_service.upload_folder
        pdf_service.upload_folder = self.test_upload_dir
    
    def tearDown(self):
        """Clean up test fixtures."""
        pdf_service.upload_folder = self.original_upload_folder
    
    def test_save_uploaded_file(self):
        """Test saving an uploaded file."""
        # Create a mock file
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        
        # Call the method
        file_id, file_path = pdf_service.save_uploaded_file(mock_file)
        
        # Check that the file was saved
        self.assertTrue(os.path.dirname(file_path) == self.test_upload_dir)
        self.assertTrue(file_id in file_path)
    
    @patch('requests.Session')
    def test_process_pdf_error_handling(self, mock_session):
        """Test that process_pdf handles errors properly."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"detail":"Missing boundary in multipart."}'
        
        # Set up the mock session to return the mock response
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_file:
            # Write some dummy content to ensure the file exists
            temp_file.write(b"dummy pdf content")
            temp_file.flush()
            
            # Call the method
            result = pdf_service.process_pdf(temp_file.name)
            
            # Check that None is returned and not causing errors
            self.assertIsNone(result)
            
            # Verify the API was called via the session
            mock_session_instance.post.assert_called_once()
    
    @patch('requests.Session')
    def test_process_pdf_success(self, mock_session):
        """Test that process_pdf handles successful responses."""
        # Create a mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"text": "Sample text", "type": "Title", "metadata": {"coordinates": {"page_number": 1, "points": [{"x": 0, "y": 0}, {"x": 0, "y": 1}, {"x": 1, "y": 1}, {"x": 1, "y": 0}]}}}]
        
        # Set up the mock session to return the mock response
        mock_session_instance = MagicMock()
        mock_session_instance.post.return_value = mock_response
        mock_session.return_value = mock_session_instance
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf') as temp_file:
            # Write some dummy content to ensure the file exists
            temp_file.write(b"dummy pdf content")
            temp_file.flush()
            
            # Call the method
            result = pdf_service.process_pdf(temp_file.name)
            
            # Check that result contains the expected elements
            self.assertIsNotNone(result)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["text"], "Sample text")
            
            # Verify the API was called via the session
            mock_session_instance.post.assert_called_once()

if __name__ == '__main__':
    unittest.main() 