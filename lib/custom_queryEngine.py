from typing import List, Optional, Any
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.core.response import Response
from llama_index.core.schema import NodeWithScore
from llama_index.core.callbacks import CallbackManager
from llama_index.core import QueryBundle
import logging

logger = logging.getLogger(__name__)


class MetadataCitationQueryEngine(CitationQueryEngine):
    """
    Extended CitationQueryEngine that formats and displays metadata
    from the extracted filename information.
    """
    
    def __init__(
        self,
        *args,
        show_metadata: bool = True,
        metadata_fields: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize the MetadataCitationQueryEngine.
        
        Args:
            show_metadata: Whether to display metadata in responses
            metadata_fields: Specific metadata fields to display (None = all)
            *args, **kwargs: Arguments passed to parent CitationQueryEngine
        """
        super().__init__(*args, **kwargs)
        self.show_metadata = show_metadata
        self.metadata_fields = metadata_fields or [
            'date', 'newspaper', 'title', 'page', 'document_type', "day", "month", "year"
        ]
    
    def _format_metadata(self, metadata: dict) -> str:
        """
        Format metadata dictionary into a readable string.
        
        Args:
            metadata: Dictionary containing metadata
            
        Returns:
            Formatted metadata string
        """
        formatted_parts = []
        
        # Check document type
        doc_type = metadata.get('document_type', 'general')
        
        if doc_type == 'newspaper_article':
            # Format newspaper article metadata
            if 'newspaper' in metadata:
                formatted_parts.append(f"📰 {metadata['newspaper']}")
            
            if 'date' in metadata:
                formatted_parts.append(f"📅 {metadata['date']}")
            
            if 'page' in metadata:
                formatted_parts.append(f"📄 Page {metadata['page']}")
            
            if 'title' in metadata:
                formatted_parts.append(f"📰 {metadata['title']}")

        else:
            # Format general document metadata
            if 'title' in metadata:
                formatted_parts.append(f"📄 {metadata['title']}")
        
        # Add source filename if available
        if 'source_filename' in metadata:
            formatted_parts.append(f"🗂️ File: {metadata['source_filename']}")
        
        return " | ".join(formatted_parts) if formatted_parts else "No metadata available"
    
def _create_citation_nodes(self, nodes: List[NodeWithScore]) -> List[NodeWithScore]:
    """
    Override to inject readable metadata into each citation node
    so the LLM can see it and use it in its response generation.
    """
    citation_nodes = super()._create_citation_nodes(nodes)

    for node_with_score in citation_nodes:
        node = node_with_score.node
        metadata = node.metadata

        if metadata:
            # Build a readable metadata header
            title = metadata.get('title', 'Unknown')
            newspaper = metadata.get('newspaper', 'Unknown')
            date = metadata.get('date', 'Unknown')
            page = metadata.get('page', 'Unknown')
            filename = metadata.get('source_filename', 'Unknown')

            # Break down components for clarity
            doc_header_lines = [
                f"Document Metadata:",
                f"- Title: {title}",
                f"- Newspaper: {newspaper}",
                f"- Date: {date}",
                f"- Page: {page}",
                f"- File: {filename}",
            ]

            metadata_header = "\n".join(doc_header_lines)

            # Get original content
            original_text = node.get_content()

            # Inject metadata above the content
            node.text = f"{metadata_header}\n\n{original_text}"

    return citation_nodes


def create_metadata_query_engine(
    index,
    similarity_top_k: int = 3,
    citation_chunk_size: int = 512,
    streaming: bool = True,
    # show_metadata: bool = True,
    verbose: bool = True
    ):
    """
    Factory function to create a MetadataCitationQueryEngine.
    
    Args:
        index: The vector store index
        similarity_top_k: Number of similar chunks to retrieve
        citation_chunk_size: Size of citation chunks
        streaming: Whether to enable streaming
        show_metadata: Whether to display metadata
        verbose: Whether to enable verbose output
        
    Returns:
        MetadataCitationQueryEngine instance
    """
    return MetadataCitationQueryEngine.from_args(
        index,
        similarity_top_k=similarity_top_k,
        citation_chunk_size=citation_chunk_size,
        streaming=True,
        verbose=verbose,
        show_metadata=True,
        response_mode="refine"
    )

def format_response(response):
    """
    Format the response
    """
    return f"\n {response}"

def format_metadata(response, show_full_text: bool = False) -> str:
    """
    Format the metadata into a single string for display.
    
    Args:
        response: Query response object
        show_full_text: Whether to show full source text or truncated version

    Returns:
        A formatted string of the response and associated metadata.
    """
    output = []

    for i, source_node in enumerate(response.source_nodes, 1):
        output.append(f"\n--- Source {i} ---")

        metadata = source_node.node.metadata
        if metadata:
            doc_type = metadata.get('document_type', 'general')

            output.append(f"📰 Newspaper: {metadata.get('newspaper', 'Unknown')}")
            output.append(f"📅 Date: {metadata.get('date', 'Unknown')}")
            output.append(f"📄 Page: {metadata.get('page', 'Unknown')}")
            output.append(f"📌 Article Title: {metadata.get('title', 'Unknown')}")
            output.append(f"🗂️ Source File: {metadata.get('source_filename', 'Unknown')}")

        # Display text content
        text = source_node.node.get_text()
        if show_full_text:
            output.append(f"\nContent:\n{text}")
        else:
            max_chars = 500
            if len(text) > max_chars:
                output.append(f"\nContent (first {max_chars} chars):\n{text[:max_chars]}...")
            else:
                output.append(f"\nContent:\n{text}")

        output.append("-" * 40)

    return "\n".join(output)