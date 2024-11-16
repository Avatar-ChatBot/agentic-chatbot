from langchain_fireworks import ChatFireworks
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore

from langchain_community.utilities.sql_database import SQLDatabase

from dotenv import load_dotenv
import os

from langchain_together import ChatTogether

load_dotenv()

# llm = ChatGroq(model_name="llama-3.2-90b-text-preview", temperature=0)
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
# llm = ChatGroq(model_name="llama3-groq-70b-8192-tool-use-preview", temperature=0)
# llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
# llm = ChatTogether(model="meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo", temperature=0)
# llm_v3p1_405b = ChatFireworks(
#     model="accounts/fireworks/models/llama-v3p1-405b-instruct", temperature=0
# )
llm_4o_mini = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = PineconeVectorStore(embedding=embeddings, index_name="informasi-umum-itb")
db = SQLDatabase.from_uri(os.getenv("SUPABASE_URI"))
