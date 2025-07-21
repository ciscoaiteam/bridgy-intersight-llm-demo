import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from tools.pdf_loader import PDFLoader
from config import setup_langsmith
import logging
import re

logger = logging.getLogger(__name__)

class AIPodExpert:
    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=os.getenv("LLM_MODEL", "gemma-2-9b"),
            base_url=os.getenv("LLM_SERVICE_URL", "http://vllm-server:8000/v1"),
            api_key=os.getenv("LLM_API_KEY", "llm-api-key"),
            temperature=0.0
        )
        self.pdf_loader = PDFLoader()

        # Create prompt template
        self.prompt = ChatPromptTemplate.from_template("""
        You are a Cisco AI Pods expert. Use the provided documentation context to answer the question accurately.

        When responding about AI Pods, focus on:
        - Hardware specifications and requirements for different LLM sizes
        - Appropriate AI Pod configurations for specific workloads
        - Deployment and operational best practices
        - Performance characteristics and scaling guidelines

        If the question asks about specific LLM sizes (like 40B models), provide detailed hardware recommendations.

        Question: {question}
        Documentation Context: {context}

        FORMAT INSTRUCTIONS:
        Format your response in HTML instead of Markdown. Use appropriate HTML tags like:
        - <h4> for headings
        - <p> for paragraphs
        - <ul>, <ol>, <li> for lists
        - <code> for code snippets
        - <b>, <i>, <u> for text formatting
        - <table>, <tr>, <th>, <td> for tables with proper structure
        - <a href="URL">link text</a> for links

        IMPORTANT: For each claim or technical detail in your response, include a reference to the specific part of the documentation where this information was found. Use a format like: "<p><small>(Reference: AI Infrastructure Pods, p. X)</small></p>" or similar appropriate citation.

        At the end of your response, include a "<h4>Sources</h4>" section that lists all the documentation references you used as an ordered list with <ol> and <li> tags. All href should use the following base url https://64.101.226.221:8443/pdf/

        Provide a detailed and technical response based on the actual documentation, formatted in HTML:
        """)

        # Create chain using the new RunnableSequence pattern
        self.chain = self.prompt | self.llm

    def markdown_to_html(self, text):
        """Convert Markdown formatting to HTML with proper indentation."""
        # First pass: convert all Markdown to preliminary HTML without list processing
        # Replace headings first to avoid interference with list processing
        text = re.sub(r'^\s*####\s+(.*?)\s*$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*###\s+(.*?)\s*$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        
        # Process reference formatting
        text = re.sub(r'\[Reference:\s+Page\s+(\d+)\s+of\s+([^\]]+?)\s*\]', 
                     r'<p><small>(Reference: \2, p. \1)</small></p>', text)
        text = re.sub(r'\[Reference:\s+([^,]+),\s+p\.?\s+(\d+)\]', 
                     r'<p><small>(Reference: \1, p. \2)</small></p>', text)
        
        # Second pass: process the lists properly
        # We'll split the text into blocks and process them separately to avoid nesting issues
        blocks = re.split(r'(\n\s*\n+)', text)
        processed_blocks = []
        
        for block in blocks:
            # Skip empty blocks or just whitespace/newlines
            if not block.strip():
                processed_blocks.append(block)
                continue
            
            # Check if block contains list items
            if re.search(r'^\s*[*-]\s+|^\s*\d+\.\s+', block, flags=re.MULTILINE):
                # Convert bullet points and numbered lists to list items
                block = re.sub(r'^\s*[*-]\s+(.*?)$', r'<li>\1</li>', block, flags=re.MULTILINE)
                block = re.sub(r'^\s*\d+\.\s+(.*?)$', r'<li>\1</li>', block, flags=re.MULTILINE)
                
                # Wrap all consecutive list items with a single ul tag
                if '<li>' in block:
                    block = f'<ul style="margin-left: 20px;">\n{block}\n</ul>'
            
            processed_blocks.append(block)
        
        # Rejoin the blocks
        text = ''.join(processed_blocks)
        
        # Clean up any potential HTML issues
        # Remove any empty lists
        text = re.sub(r'<ul[^>]*>\s*</ul>', '', text)
        
        # Fix spacing around headings
        text = re.sub(r'(</h[34]>)\s*(\S)', r'\1\n\n\2', text)
        text = re.sub(r'(\S)\s*(<h[34]>)', r'\1\n\n\2', text)
        
        # Make sure there's proper spacing between lists and other elements
        text = re.sub(r'(</ul>)\s*(\S)', r'\1\n\n\2', text)
        text = re.sub(r'(\S)\s*(<ul)', r'\1\n\n\2', text)
        
        # First clean up the Sources section before special processing
        # Remove any existing lists within Sources sections
        def clean_sources_section(match):
            heading = match.group(1)
            content = match.group(2)
            
            # Remove any existing list tags from the content
            content = re.sub(r'</?[ou]l[^>]*>', '', content)
            content = re.sub(r'<li>(.*?)</li>', r'\1', content)
            
            return f"<h4>{heading}</h4>\n{content}"
        
        # First clean up any Sources sections that might have lists already
        text = re.sub(r'<h4>(Sources|References)</h4>\s*(.*?)(?=<h\d>|$)',
                     clean_sources_section, text, flags=re.DOTALL)
        
        # Now format the cleaned Sources section properly
        def format_sources(match):
            sources_title = match.group(1)
            content = match.group(2).strip()
            
            # Split into lines and create list items, skipping empty lines
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            
            if not lines:  # If no sources found
                return f"<h4>{sources_title}</h4>"
            
            sources_html = f"<h4>{sources_title}</h4>\n<ul style=\"margin-left: 20px;\">\n"
            
            # Process each line, ensuring it's not duplicated or empty
            processed_lines = []
            for line in lines:
                if line and line not in processed_lines:
                    processed_lines.append(line)
                    sources_html += f"<li>{line}</li>\n"
            
            sources_html += "</ul>"
            return sources_html
        
        # Finally, format Sources section with proper list
        text = re.sub(r'<h4>(Sources|References)</h4>\s*(.*?)(?=<h\d>|$)',
                     format_sources, text, flags=re.DOTALL)
        
        # Remove any empty list structures that might have been created
        text = re.sub(r'<ul[^>]*>\s*</ul>', '', text)
        
        return text

    def get_response(self, question: str) -> str:
        try:
            # Get relevant context from PDF documents
            context = self.pdf_loader.get_relevant_context(question)
            
            # Generate response
            response = self.chain.invoke({
                "question": question,
                "context": context
            })
            
            # Extract just the content from the response
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, dict) and 'content' in response:
                content = response['content']
            elif isinstance(response, str):
                content = response
            else:
                # Try to convert the response to a string if it's not already
                content = str(response)
                
            # Ensure Markdown lists are converted to HTML
            content = self.markdown_to_html(content)
            
            return content

        except Exception as e:
            raise Exception(f"AI Pods Expert error: {str(e)}")
