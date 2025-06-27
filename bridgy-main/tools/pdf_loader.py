import os
import logging
from typing import List
import tempfile
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
# from langchain.embeddings import HuggingFaceEmbeddings  # Updated to use local embeddings
# from langchain_huggingface import HuggingFaceEmbeddings # Updated to use local embeddings
from langchain_community.embeddings import HuggingFaceEmbeddings

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PDFLoader:
    def __init__(self, pdf_dir="pdf"):
        self.pdf_dir = pdf_dir
        self.vector_store = None
        self.init_vector_store()

    def init_vector_store(self):
        """Initialize the vector store with PDF documents."""
        try:
            pdf_files = self._get_pdf_files()
            if not pdf_files:
                logger.warning(f"No PDF files found in {self.pdf_dir}. Using mock content.")
                self._create_mock_vector_store()
                return

            all_docs = []
            for pdf_file in pdf_files:
                logger.info(f"Loading PDF: {pdf_file}")
                loader = PyPDFLoader(pdf_file)
                docs = loader.load()
                all_docs.extend(docs)
                logger.info(f"Loaded {len(docs)} pages from {pdf_file}")

            if not all_docs:
                logger.warning("No content extracted from PDFs. Using mock content.")
                self._create_mock_vector_store()
                return

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100
            )
            splits = text_splitter.split_documents(all_docs)
            logger.info(f"Created {len(splits)} document chunks for vectorization")

            # Create vector store using local embeddings
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2", encode_kwargs={"normalize_embeddings": True})
            self.vector_store = FAISS.from_documents(splits, embeddings)
            logger.info("Vector store successfully created with real PDF content")

        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            logger.warning("Using mock content due to initialization error")
            self._create_mock_vector_store()

    def _get_pdf_files(self) -> List[str]:
        """Get list of PDF files in the directory."""
        if not os.path.exists(self.pdf_dir):
            logger.warning(f"PDF directory {self.pdf_dir} does not exist")
            return []

        pdf_files = []
        for filename in os.listdir(self.pdf_dir):
            if filename.lower().endswith('.pdf'):
                pdf_files.append(os.path.join(self.pdf_dir, filename))

        return pdf_files

    def _create_mock_vector_store(self):
        """Create a mock vector store for testing."""
        mock_docs = [
            "Cisco AI Pods are engineered specifically for AI workloads. They provide optimized infrastructure for various LLM sizes.",
            "For 40B parameter models, Cisco recommends a minimum of 8 GPUs with at least 80GB memory each.",
            "Deployment best practices include proper cooling, network bandwidth of at least 100Gbps between nodes, and redundant power supplies.",
            "Performance scaling is nearly linear up to 32 GPUs for most common LLM architectures.",
            "AI Pods can be configured with different GPU options including NVIDIA H100, A100, and L40S depending on workload requirements."
        ]

        from langchain.schema.document import Document
        doc_objects = [Document(page_content=text, metadata={"source": "mock"}) for text in mock_docs]

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vector_store = FAISS.from_documents(doc_objects, embeddings)
        logger.warning("Initialized with mock vector store")

    def get_relevant_context(self, query: str, k: int = 5) -> str:
        """Retrieve relevant context from PDFs based on the query."""
        try:
            if not self.vector_store:
                logger.warning("Vector store not initialized. Returning empty context.")
                return ""

            docs = self.vector_store.similarity_search(query, k=k)
            if not docs:
                logger.warning("No relevant documents found")
                return "No relevant documentation found."

            # Combine the content from the retrieved documents with page number information
            context_parts = []
            for doc in docs:
                page_number = doc.metadata.get('page', 'unknown page')
                section = doc.metadata.get('source', 'AI Infrastructure Pods document')
                context_part = f"--- BEGIN EXCERPT FROM {section} (Page {page_number}) ---\n"
                context_part += doc.page_content
                context_part += f"\n--- END EXCERPT FROM {section} (Page {page_number}) ---\n"
                context_parts.append(context_part)

            context = "\n\n".join(context_parts)
            return context
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return f"Error retrieving information: {str(e)}"
