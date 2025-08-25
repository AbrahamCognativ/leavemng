"""
Document conversion utilities for converting DOCX files to PDF for preview purposes.
"""
import os
import tempfile
from pathlib import Path
from typing import Optional
import logging

try:
    from docx import Document
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
    CONVERSION_AVAILABLE = True
except ImportError:
    CONVERSION_AVAILABLE = False

logger = logging.getLogger(__name__)

class DocumentConverter:
    """Handles conversion of DOCX files to PDF for preview purposes."""
    
    @staticmethod
    def is_conversion_available() -> bool:
        """Check if document conversion libraries are available."""
        return CONVERSION_AVAILABLE
    
    @staticmethod
    def convert_docx_to_pdf(docx_path: str, output_path: Optional[str] = None) -> str:
        """
        Convert a DOCX file to PDF.
        
        Args:
            docx_path: Path to the input DOCX file
            output_path: Optional path for the output PDF file. If None, creates a temp file.
            
        Returns:
            Path to the generated PDF file
            
        Raises:
            ValueError: If conversion libraries are not available
            FileNotFoundError: If the input file doesn't exist
            Exception: If conversion fails
        """
        if not CONVERSION_AVAILABLE:
            raise ValueError("Document conversion libraries not available. Please install python-docx and reportlab.")
        
        if not os.path.exists(docx_path):
            raise FileNotFoundError(f"Input file not found: {docx_path}")
        
        try:
            # Create output path if not provided
            if output_path is None:
                temp_dir = tempfile.gettempdir()
                base_name = Path(docx_path).stem
                output_path = os.path.join(temp_dir, f"{base_name}_preview.pdf")
            
            # Load the DOCX document
            doc = Document(docx_path)
            
            # Create PDF document
            pdf_doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                spaceBefore=12,
                alignment=TA_LEFT
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=12,
                alignment=TA_JUSTIFY,
                leftIndent=0,
                rightIndent=0
            )
            
            # Build content
            story = []
            
            # Process each paragraph in the document
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    # Add space for empty paragraphs
                    story.append(Spacer(1, 6))
                    continue
                
                # Determine style based on paragraph formatting
                style = normal_style
                
                # Check if it's a heading (simple heuristic)
                if len(text) < 100 and (
                    text.isupper() or 
                    paragraph.style.name.startswith('Heading') or
                    any(run.bold for run in paragraph.runs if run.text.strip())
                ):
                    if len(story) == 0:  # First heading is likely a title
                        style = title_style
                    else:
                        style = heading_style
                
                # Escape special characters for ReportLab
                text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                # Create paragraph
                para = Paragraph(text, style)
                story.append(para)
            
            # If no content was found, add a message
            if not story:
                story.append(Paragraph("This document appears to be empty or contains only formatting.", normal_style))
            
            # Build the PDF
            pdf_doc.build(story)
            
            logger.info(f"Successfully converted DOCX to PDF: {docx_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to convert DOCX to PDF: {docx_path}. Error: {str(e)}")
            raise Exception(f"Document conversion failed: {str(e)}")
    
    @staticmethod
    def get_preview_pdf_path(original_file_path: str) -> str:
        """
        Get the path where the preview PDF should be stored.
        
        Args:
            original_file_path: Path to the original DOCX file
            
        Returns:
            Path where the preview PDF should be stored
        """
        file_path = Path(original_file_path)
        preview_dir = file_path.parent / "previews"
        preview_dir.mkdir(exist_ok=True)
        
        preview_filename = f"{file_path.stem}_preview.pdf"
        return str(preview_dir / preview_filename)
    
    @staticmethod
    def ensure_preview_exists(docx_path: str) -> str:
        """
        Ensure a preview PDF exists for the given DOCX file.
        Creates the preview if it doesn't exist or if the original file is newer.
        
        Args:
            docx_path: Path to the DOCX file
            
        Returns:
            Path to the preview PDF file
        """
        preview_path = DocumentConverter.get_preview_pdf_path(docx_path)
        
        # Check if preview exists and is newer than original
        if (os.path.exists(preview_path) and 
            os.path.getmtime(preview_path) > os.path.getmtime(docx_path)):
            return preview_path
        
        # Create or update the preview
        return DocumentConverter.convert_docx_to_pdf(docx_path, preview_path)
    
    @staticmethod
    def convert_to_pdf(input_path: str, output_path: str) -> str:
        """
        Convert a document to PDF. Currently supports DOCX files.
        
        Args:
            input_path: Path to the input document
            output_path: Path for the output PDF file
            
        Returns:
            Path to the generated PDF file
        """
        file_ext = Path(input_path).suffix.lower()
        
        if file_ext in ['.doc', '.docx']:
            return DocumentConverter.convert_docx_to_pdf(input_path, output_path)
        else:
            raise ValueError(f"Unsupported file type for conversion: {file_ext}")