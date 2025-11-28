from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
import os
import warnings

load_dotenv()

# Suppress Qdrant API key warning for local HTTP connections
warnings.filterwarnings("ignore", message=".*Api key is used with an insecure connection.*")

# llm = ChatGroq(model_name="llama-3.2-90b-vision-preview", temperature=0)
# llm = ChatGroq(model_name="llama-3.1-70b-versatile", temperature=0)
# llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
# llm = ChatGroq(model_name="llama3-groq-70b-8192-tool-use-preview", temperature=0)
# llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
# llm = ChatTogether(model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", temperature=0)
# llm = ChatFireworks(
#     model="accounts/fireworks/models/llama-v3p1-70b-instruct", temperature=0
# )
# llm = ChatTogether(model="deepseek-ai/DeepSeek-V3", temperature=0)
# llm = ChatTogether(model="Qwen/QwQ-32B", temperature=0)
# OpenRouter LLM configuration with Qwen3 2335B
llm = ChatOpenAI(
    model="qwen/qwen3-235b-a22b",
    temperature=0,
    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": os.getenv("SITE_URL", "https://your-site.com"),
        "X-Title": os.getenv("APP_NAME", "ITB Chatbot"),
    },
    timeout=60,
)
llm_4o_mini = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# jina_embeddings = JinaEmbeddings(model="jina-embeddings-v3-large")
# vectorstore = PineconeVectorStore(
#     embedding=jina_embeddings, index_name="informasi-umum-itb-jina"
# )

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# Qdrant vector store initialization
# Only use API key if provided (required for HTTPS, optional for local HTTP)
qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
qdrant_api_key = os.getenv("QDRANT_API_KEY")

# Initialize Qdrant client - API key is optional for local HTTP connections
if qdrant_api_key:
    qdrant_client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
    )
else:
    # For local development without API key
    qdrant_client = QdrantClient(url=qdrant_url)

vectorstore = QdrantVectorStore(
    client=qdrant_client,
    collection_name=os.getenv("QDRANT_COLLECTION_NAME", "informasi-umum-itb"),
    embedding=embeddings,
)
# db = SQLDatabase.from_uri(os.getenv("SUPABASE_URI"))
