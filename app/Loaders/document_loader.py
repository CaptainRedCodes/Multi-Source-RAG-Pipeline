
# for plain text pdfs
import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_community.document_loaders.csv_loader import CSVLoader 

class DocumentLoader:
    """ For PDF's(Only Text) and CSV's"""
    def __init__(self):
        self.stats = {
            'total_files': 0,
            'sucessfull': 0,
            'failed': 0
        }

    def _enrich_metadata(self, doc: Document, file_path: Path, file_type: str,additional_metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        Enrich document metadata with standard and custom fields.
        """

        doc.metadata.update({
            'source_file': file_path.name,
            'source_path': str(file_path.absolute()),
            'file_type': file_type,
            'file_size_bytes': file_path.stat().st_size,
            'ingested_at': str(datetime.datetime.now().isoformat()),
            'content_length': len(doc.page_content)
        })
        
        if additional_metadata:
            doc.metadata.update(additional_metadata)
        
        return doc

        
    def load_pdfs(self,pdf_dir:str,additional_metadata:Optional[Dict[str,Any]] = None) -> List[Document]:
        print("Loading Documents")
        all_docs = []
        dir_path = Path(pdf_dir).resolve()
        print("resolved_path",{dir_path})

        if not dir_path:
            raise ValueError("Invalid Directory Path")
        

        pdf_files = list(dir_path.rglob("**/*.pdf"))

        self.stats['total_files']+=len(pdf_files)

        for idx,pdf_path in enumerate(pdf_files):
            try:
                loader = PyMuPDFLoader(
                    file_path=str(pdf_path),
                    mode = "page",
                    extract_images=True,
                    extract_tables='markdown'
                )

                documents = loader.load()

                if not documents:
                    raise ValueError("Error Extracting Documents")


                for doc_id,doc in enumerate(documents):
                    page_metadata = {'page_number':doc_id+1}

                    if additional_metadata:
                        page_metadata.update(additional_metadata)


                    self._enrich_metadata(doc, pdf_path, 'pdf', page_metadata)
                    doc.page_content = doc.page_content.strip()
                    if doc.page_content:
                        all_docs.append(doc)
                
                self.stats['sucessfull']+=1
                self.stats['total_files']+=1
                
            except Exception as e:
                self.stats['failed']+=1
                raise ValueError("Exception Occured",e)
            
        print("Loaded Documents")
        return all_docs

    def load_csvs(self,csv_dir: str,delimiter: str = ",",encoding: str = "utf-8",recursive: bool = True,source_column: Optional[str] = None,additional_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Load CSV documents from a directory with enhanced features.
        
        """
        all_docs = []
        dir_path = Path(csv_dir)
        
        # Validate directory
        if not dir_path.exists():
            raise ValueError("Directory path doesnt exists")
        
        if not dir_path.is_dir():
            raise ValueError("Directory doesnt exists")
        
        # Find CSV files
        pattern = "**/*.csv" if recursive else "*.csv"
        csv_files = list(dir_path.glob(pattern))
        
        if not csv_files:
            return []
        
        self.stats['total_files'] += len(csv_files)
        
        # Process each CSV
        for idx, csv_path in enumerate(csv_files, 1):
            try:
                csv_args = {
                    "delimiter": delimiter,
                    "quotechar": '"'
                }
                
                # Load CSV
                loader = CSVLoader(
                    file_path=str(csv_path),
                    encoding=encoding,
                    source_column=source_column,
                    csv_args=csv_args
                )
                
                documents = loader.load()
                
                if not documents:
                    print("No documents Loaded")
                    continue
                
                for doc_idx, doc in enumerate(documents):
                    row_metadata = {'row_number': doc_idx + 1}
                    if additional_metadata:
                        row_metadata.update(additional_metadata)
                    
                    self._enrich_metadata(doc, csv_path, 'csv', row_metadata)
                    
                    doc.page_content = doc.page_content.strip()
                    
                    if doc.page_content:
                        all_docs.append(doc)
                
                self.stats['successful'] += 1
                self.stats['total_docs'] += len(documents)
                
            except Exception as e:
                self.stats['failed'] += 1
                continue
        
        return all_docs
    
    def get_stats(self) -> Dict[str, int]:
        """Return loading statistics."""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset loading statistics."""
        self.stats = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'total_docs': 0
        }