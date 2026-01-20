# semantic chunking

from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class Chunking:
    def __init__(self) -> None:
        pass


    def recursive_text_splitter(self,docs:List[Document],chunk_size:int = 500,chunk_overlap:int=100,is_separator_regex:bool=False):
        print("Started Chunking Process")
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function = len,
                is_separator_regex = is_separator_regex)

            chunked_document = text_splitter.split_documents(docs)
        except Exception as e:
            raise ValueError("Error in Text Splitter",e)
        
        return chunked_document

#Note: Will add more chunking methods later