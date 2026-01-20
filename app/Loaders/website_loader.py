from typing import List, Optional, Sequence
from langchain_core.documents import Document
from langchain_community.document_loaders import SitemapLoader, WebBaseLoader, RecursiveUrlLoader, AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer

import datetime
import nest_asyncio

nest_asyncio.apply()

class WebLoader:

    def __init__(self):
        self.html_transformer = Html2TextTransformer()
        self.stats = {
            'successfull':0,
            'failure':0,
            'total':0
        }

    def _postprocess(self,docs:Sequence[Document],source_type:str)->List[Document]:
        """ Post-process documents by cleaning content and adding metadata. """
        processed_docs = []
        for d in docs:
            try:
                d.page_content = d.page_content.strip()
                d.metadata.update({
                    "source_type": source_type,
                    "ingested_at": str(datetime.datetime.now()),
                    "content_length": len(d.page_content)
                })

                if d.page_content:
                    processed_docs.append(d)
            
            except Exception as e:
                raise ValueError("Error in post process",e)
        
        return processed_docs


    def load_single_page(self,url:str)->List[Document]:
        """ Load a single Web Page """
        try:
            docs = WebBaseLoader(url).load()
            process =self._postprocess(docs, "web_page")
            self.stats['sucessfull']+=1
            self.stats['total']+=1
        except Exception as e:
            self.stats['failure']+=1
            raise ValueError("Error loading single page")
        
        return process


    def load_sitemap(self, sitemap_url: str, filter_urls: Optional[List[str]] = None) -> List[Document]:
        """ Load all pages from a sitemap """
        try:
            loader = SitemapLoader(sitemap_url, filter_urls=filter_urls)
            docs = loader.load()
            processed = self._postprocess(docs, "sitemap")
            self.stats['sucessfull']+=1
            self.stats['total']+=1
        except Exception as e:
            self.stats['failure']+=1
            raise ValueError("Error loading sitemap page")
        
        return processed


    def load_recursive(self, base_url: str, max_depth: int = 2) -> List[Document]:
        """  Recursively crawl a website starting from a base URL. """
        try:
            docs = RecursiveUrlLoader(
                url=base_url,
                max_depth=max_depth
            ).load()
            processed = self._postprocess(docs, "recursive")
            self.stats['sucessfull']+=1
            self.stats['total']+=1
        except Exception as e:
            self.stats['failure']+=1
            raise ValueError("Error collecting website data recusively")
        
        return processed


    def load_async_urls(self,urls: List[str])->List[Document]:
        """ Load multiple URLs asynchronously for faster processing. """
        try:
            loader = AsyncHtmlLoader(urls)
            docs = list(loader.lazy_load())

            docs = self.html_transformer.transform_documents(docs)
            processed = self._postprocess(docs, "async")
            self.stats['sucessfull']+=1
            self.stats['total']+=len(docs)
        except Exception as e:
            self.stats['failure']+=1
            raise ValueError("Error loading multiple websites ")

        return processed
