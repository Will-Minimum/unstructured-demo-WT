import logging
from services.llm_service import llm_service

logger = logging.getLogger(__name__)

class ExtractionService:
    def __init__(self):
        self.llm_service = llm_service

    def extract_information(self, elements, schema):
        """
        Extract information from PDF elements using the provided schema.
        
        Args:
            elements (list): List of elements from the PDF
            schema (dict): Schema defining the fields to extract
            
        Returns:
            dict: Extracted information mapped to schema fields
        """
        try:
            # Extract text from elements
            text = "\n\n".join([element["text"] for element in elements])
            logger.debug(f"Extracted text length: {len(text)} characters")
            
            # Extract information using LLM
            logger.info("Calling LLM to extract information")
            extraction_result = self.llm_service.extract_information(text, schema)
            logger.info("Information extracted successfully")
            
            if extraction_result is None:
                logger.error("LLM extraction returned None")
                return None
                
            return extraction_result["extracted_data"]
            
        except Exception as e:
            logger.exception(f"Error in extract_information: {e}")
            return None

# Create singleton instance
extraction_service = ExtractionService() 