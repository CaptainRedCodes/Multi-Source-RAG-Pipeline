### RAG Application

This is a simple RAG application which helps in finding related queries in large systems.

Here i have implemented it using in-house vectorDB(ChromaDB with SQLite).
Here the i have used PDF's,CSV's,Website(through scraping) as primary datasource of the RAG pipeline,
then it uses 'all-MiniLM-L6-v2' as the embedding Model to embed the chunked data.

Once done storing in the vectorDB, implemeted 2 types of Retrival Stratergies-
1) A simple retrival stratergy which retrieves data higher than the score threshold
2) A complex RAG system where it gives me detailed retrived documents with source,citation and history.

i have used Groq as my LLM provider to summarise the retrieved query for the user.

But i have found out that its not that efficient to find complex answers or answers for vague higher level questions.This is somewhat a limitation of the RAG stratergy using VectorDB's.

I have converted this into a full stack project by using Fastapi as backend and streamlit as frontend frameworks

# To host the project yourself
.env file
```
GROQ_API_KEY = ''
```

1) To run the notebook code, you can do it directly in jupyternotebook by installing required libraries
2) For Fastapi 
Installation -
```
git clone repo link
cd project-name

uv venv
source .venv/bin/activate / .venv\Scripts\activate

uv pip install -r requirements.txt

```

Once this is done

```
cd app
uvicorn main:app --reload

```

Frontend setup  
```
streamlit run app_frontend.py

```

NOTE: As chunking and embedding is done in-house, it WILL take few minutes in inititalizing the project and run. If backend project doesnt work try the notebook one.


~ :>