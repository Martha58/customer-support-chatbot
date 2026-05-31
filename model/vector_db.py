from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import re
import uuid
import os

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

pc = Pinecone(api_key=PINECONE_API_KEY)

index_name = "chatbot-faq"

if not pc.has_index(index_name):
    pc.create_index(
        name=index_name,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1"),
    )

index = pc.Index(index_name)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = PineconeVectorStore(index=index, embedding=embeddings)

# Load PDF
pdf_loader = PyPDFLoader(
    r"C:\Users\martha\OneDrive\ai_projects\customer_support_chatbot\model\ecommerce_faqs.pdf"
)

document = pdf_loader.load()

print(f"Total PDF pages: {len(document)}")

# Combine all pages into a single text
full_text = ""

for page in document:
    full_text += page.page_content + "\n"

# Split FAQs using '#' headers
faq_chunks = re.split(r'(?=# )', full_text)

docs = [
    Document(page_content=chunk.strip())
    for chunk in faq_chunks
    if chunk.strip()
]

print(f"\nTotal FAQ chunks extracted: {len(docs)}")

# Preview chunks
# for i, doc in enumerate(docs, start=1):
#     print(f"\n--- FAQ {i} ---")
#     print(doc.page_content)

# Example: Generate IDs if needed later
ids = [str(uuid.uuid4()) for _ in docs]
vector_store.add_documents(documents=docs, ids=ids)

# print(f"\nGenerated {len(ids)} unique IDs")