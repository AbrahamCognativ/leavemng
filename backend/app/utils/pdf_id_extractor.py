"""
PDF ID extraction utility for extracting ID/Passport numbers from PDF documents.
Used for bulk payslip upload feature to automatically match documents with users.
"""
import re
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    import PyPDF2
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False

logger = logging.getLogger(__name__)

class PDFIdExtractor:
    """Handles extraction of ID/Passport numbers from PDF documents."""
    
    # Common ID patterns for different formats - refined for payslip context
    ID_PATTERNS = {
        'primary_id_field': [
            r'ID\s*[:\-]?\s*(\d{6,12})',  # ID: followed by digits (most likely employee ID)
            r'Employee\s*ID\s*[:\-]?\s*(\d{4,10})',  # Employee ID: format
            r'Staff\s*ID\s*[:\-]?\s*(\d{4,10})',     # Staff ID: format
            r'EMP\s*[:\-]?\s*(\d{4,8})',             # EMP: format
        ],
        'passport': [
            r'Passport\s*[:\-]?\s*([A-Z]{1,2}\d{6,9})',  # Passport: followed by passport format
            r'[A-Z]{1,2}\d{6,9}(?!\d)',  # Standard passport format (not followed by more digits)
        ],
        'national_id_specific': [
            r'National\s*ID\s*[:\-]?\s*(\d{6,12})',  # National ID: format
            r'Citizen\s*ID\s*[:\-]?\s*(\d{6,12})',   # Citizen ID: format
        ],
        'fallback_patterns': [
            r'\b\d{8}\b(?!\d)',        # Exactly 8 digits (common ID length)
            r'\b\d{7}\b(?!\d)',        # Exactly 7 digits
            r'\b\d{6}\b(?!\d)',        # Exactly 6 digits
        ]
    }
    
    # Patterns to EXCLUDE (these are not employee IDs)
    EXCLUDE_PATTERNS = [
        r'PIN\s*[:\-]?\s*[A-Z0-9]+',     # Tax PIN numbers
        r'NHIF\s*[:\-]?\s*\d+',          # NHIF numbers
        r'NSSF\s*[:\-]?\s*\d+',          # NSSF numbers
        r'Bank\s*Acc\s*[:\-]?\s*\d+',    # Bank account numbers
        r'Account\s*[:\-]?\s*\d+',       # Account numbers
        r'Branch\s*[:\-]?\s*\d+',        # Branch codes
        r'\d{4}/\d{2}/\d{2}',            # Date formats
        r'\d{2}/\d{2}/\d{4}',            # Date formats
        r'CREATED\s*[:\-]?\s*\d+',       # Creation dates/codes
        r'\b\d{10,}\b',                  # Very long numbers (likely account numbers)
    ]
    
    @staticmethod
    def is_pdf_processing_available() -> bool:
        """Check if PDF processing libraries are available."""
        return PDF_PROCESSING_AVAILABLE
    
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
            
        Raises:
            ValueError: If PDF processing is not available
            FileNotFoundError: If the PDF file doesn't exist
            Exception: If text extraction fails
        """
        if not PDF_PROCESSING_AVAILABLE:
            raise ValueError("PDF processing library (PyPDF2) not available.")
        
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            text_content = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
            
            return text_content.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_path}: {str(e)}")
            raise Exception(f"PDF text extraction failed: {str(e)}")
    
    @staticmethod
    def extract_ids_from_text(text: str, patterns: List[str] = None) -> List[str]:
        """
        Extract ID numbers from text using refined regex patterns with exclusion logic.
        
        Args:
            text: Text content to search
            patterns: Optional custom patterns to use
            
        Returns:
            List of found ID numbers (prioritized and filtered)
        """
        if patterns is None:
            # Use prioritized pattern groups
            all_patterns = []
            # Priority order: primary ID fields first, then fallbacks
            for group_name in ['primary_id_field', 'passport', 'national_id_specific', 'fallback_patterns']:
                if group_name in PDFIdExtractor.ID_PATTERNS:
                    all_patterns.extend(PDFIdExtractor.ID_PATTERNS[group_name])
            patterns = all_patterns
        
        found_ids = []
        text_upper = text.upper()  # Convert to uppercase for better matching
        
        # First, check for excluded patterns and remove those areas from text
        excluded_areas = []
        for exclude_pattern in PDFIdExtractor.EXCLUDE_PATTERNS:
            for match in re.finditer(exclude_pattern, text_upper, re.IGNORECASE):
                excluded_areas.append((match.start(), match.end()))
        
        # Extract IDs using patterns
        for pattern in patterns:
            matches = re.finditer(pattern, text_upper, re.IGNORECASE)
            for match in matches:
                # Check if this match overlaps with any excluded area
                match_start, match_end = match.start(), match.end()
                is_excluded = any(
                    not (match_end <= ex_start or match_start >= ex_end)
                    for ex_start, ex_end in excluded_areas
                )
                
                if not is_excluded:
                    # Handle patterns with capture groups
                    if match.groups():
                        id_value = match.group(1).strip()
                    else:
                        id_value = match.group(0).strip()
                    
                    if id_value and id_value not in found_ids:
                        found_ids.append(id_value)
        
        return found_ids
    
    @staticmethod
    def extract_ids_from_pdf(pdf_path: str, patterns: List[str] = None) -> List[str]:
        """
        Extract ID numbers directly from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            patterns: Optional custom patterns to use
            
        Returns:
            List of found ID numbers
        """
        try:
            text = PDFIdExtractor.extract_text_from_pdf(pdf_path)
            return PDFIdExtractor.extract_ids_from_text(text, patterns)
        except Exception as e:
            logger.error(f"Failed to extract IDs from PDF {pdf_path}: {str(e)}")
            return []
    
    @staticmethod
    def extract_payslip_info(pdf_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive information from a payslip PDF.
        
        Args:
            pdf_path: Path to the payslip PDF
            
        Returns:
            Dictionary containing extracted information
        """
        result = {
            'file_path': pdf_path,
            'file_name': Path(pdf_path).name,
            'extracted_ids': [],
            'text_content': '',
            'extraction_success': False,
            'error_message': None
        }
        
        try:
            # Extract text content
            text = PDFIdExtractor.extract_text_from_pdf(pdf_path)
            result['text_content'] = text
            
            # Extract ID numbers
            ids = PDFIdExtractor.extract_ids_from_text(text)
            result['extracted_ids'] = ids
            
            result['extraction_success'] = True
            logger.info(f"Successfully extracted {len(ids)} IDs from {pdf_path}")
            
        except Exception as e:
            result['error_message'] = str(e)
            logger.error(f"Failed to process payslip {pdf_path}: {str(e)}")
        
        return result
    
    @staticmethod
    def validate_id_format(id_number: str, id_type: str = 'auto') -> bool:
        """
        Validate if an ID number matches expected format.
        
        Args:
            id_number: The ID number to validate
            id_type: Type of ID ('passport', 'national_id', 'employee_id', 'auto')
            
        Returns:
            True if ID format is valid
        """
        if not id_number or not id_number.strip():
            return False
        
        id_clean = id_number.strip().upper()
        
        if id_type == 'auto':
            # Check against all patterns
            for pattern_group in PDFIdExtractor.ID_PATTERNS.values():
                for pattern in pattern_group:
                    if re.match(f'^{pattern}$', id_clean):
                        return True
            return False
        
        # Check against specific type patterns
        if id_type in PDFIdExtractor.ID_PATTERNS:
            for pattern in PDFIdExtractor.ID_PATTERNS[id_type]:
                if re.match(f'^{pattern}$', id_clean):
                    return True
        
        return False
    
    @staticmethod
    def get_most_likely_id(ids: List[str]) -> Optional[str]:
        """
        Get the most likely employee ID from a list of extracted IDs.
        Uses refined heuristics prioritizing actual employee IDs.
        
        Args:
            ids: List of extracted ID numbers
            
        Returns:
            Most likely employee ID or None if no good candidate
        """
        if not ids:
            return None
        
        if len(ids) == 1:
            return ids[0]
        
        # Score IDs based on employee ID criteria
        scored_ids = []
        for id_num in ids:
            score = 0
            id_clean = id_num.strip()
            
            # Strongly prefer numeric IDs (most employee IDs are numeric)
            if re.match(r'^\d+$', id_clean):
                score += 50
            
            # Prefer common employee ID lengths (6-10 digits)
            if 6 <= len(id_clean) <= 10:
                score += 30
            elif 4 <= len(id_clean) <= 5:
                score += 20  # Shorter IDs still possible
            elif len(id_clean) > 10:
                score -= 20  # Very long numbers likely not employee IDs
            
            # Prefer 8-digit IDs (very common for employee IDs)
            if len(id_clean) == 8:
                score += 25
            
            # Prefer 7-digit IDs (also common)
            if len(id_clean) == 7:
                score += 20
            
            # Prefer 6-digit IDs
            if len(id_clean) == 6:
                score += 15
            
            # Slightly penalize very short IDs (might be codes)
            if len(id_clean) < 4:
                score -= 10
            
            # Penalize IDs that look like PIN numbers (contain letters at end)
            if re.match(r'^\d+[A-Z]+$', id_clean):
                score -= 30
            
            # Penalize very long numbers (likely account numbers)
            if len(id_clean) > 12:
                score -= 40
            
            scored_ids.append((score, id_clean))
        
        # Return the highest scored ID
        scored_ids.sort(key=lambda x: x[0], reverse=True)
        return scored_ids[0][1]