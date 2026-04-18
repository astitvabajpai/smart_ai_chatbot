import hashlib
import shutil
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from app.core.config import get_settings

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter


class DocumentProcessor:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],
        )

    def save_upload(self, source_path: Path) -> Path:
        target_path = self.settings.upload_dir / source_path.name
        shutil.copy2(source_path, target_path)
        return target_path

    def load_pdf(self, pdf_path: Path) -> list[Document]:
        loader = PyPDFLoader(str(pdf_path))
        pages = loader.load()
        for page in pages:
            page.metadata["file_name"] = pdf_path.name
            page.metadata["document_id"] = self._document_id(pdf_path)
        return self.splitter.split_documents(pages)

    def _document_id(self, pdf_path: Path) -> str:
        return hashlib.md5(str(pdf_path.resolve()).encode("utf-8")).hexdigest()
