"""
metadata_extractor.py
Extracts metadata from filenames for LlamaIndex documents
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def extract_metadata_from_filename(filename: str) -> Dict[str, Any]:
    """
    Extract metadata from filename based on different patterns.
    
    Args:
        filename: The filename to extract metadata from
        
    Returns:
        Dictionary containing extracted metadata
    """
    # Remove file extension if present
    name = Path(filename).stem
    
    # Initialize metadata dict
    metadata = {
        "source_filename": filename,
        "extracted": True
    }
    
    # Example: "18410521 p3 Southern Australian 71614658 NZ separate colony from NSW"
    pattern1 = r'^(\d{8})\s+p(\d+)\s+([^0-9]+?)\s+\d+\s+(.+)$'
    match1 = re.match(pattern1, name)
    
    if match1:
        date_str = match1.group(1)
        page_num = match1.group(2)
        newspaper = match1.group(3).strip()
        title = match1.group(4).strip()
        
        # Parse date (YYYYMMDD format)
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            
            # Validate date
            date_obj = datetime(year, month, day)
            
            metadata.update({
                "date": date_obj.strftime("%Y-%m-%d"),
                "year": year,
                "month": month,
                "day": day,
                "page": int(page_num),
                "newspaper": newspaper,
                "title": title,
            })
        except (ValueError, IndexError):
            # If date parsing fails, treat as regular filename
            metadata.update({
                "title": name,
                "document_type": "general"
            })
    
    # Example: "18410521 p3 Southern Australian NZ separate colony from NSW"
    else:
        pattern2 = r'^(\d{8})\s+p(\d+)\s+([^0-9]+?)\s+([^0-9].+)$'
        match2 = re.match(pattern2, name)
        
        if match2:
            date_str = match2.group(1)
            page_num = match2.group(2)
            newspaper = match2.group(3).strip()
            title = match2.group(4).strip()
            
            try:
                year = int(date_str[:4])
                month = int(date_str[4:6])
                day = int(date_str[6:8])
                
                date_obj = datetime(year, month, day)
                
                metadata.update({
                    "date": date_obj.strftime("%Y-%m-%d"),
                    "year": year,
                    "month": month,
                    "day": day,
                    "page": int(page_num),
                    "newspaper": newspaper,
                    "title": title,
                    "document_type": "newspaper_article"
                })
            except (ValueError, IndexError):
                metadata.update({
                    "title": name,
                    "document_type": "general"
                })
        else:
            # Default case: use the whole filename as title
            metadata.update({
                "title": name,
                "document_type": "general"
            })
    
    return metadata


def create_metadata_fn(file_path: str) -> Dict[str, Any]:
    """
    Function to be used with SimpleDirectoryReader's file_metadata parameter.
    
    Args:
        file_path: Path to the file being processed
        
    Returns:
        Dictionary of metadata to be added to the document
    """
    filename = Path(file_path).name
    return extract_metadata_from_filename(filename)