from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_together import ChatTogether

load_dotenv()

# llm = ChatGroq(model_name="llama-3.2-90b-vision-preview", temperature=0)
# llm = ChatGroq(model_name="llama-3.1-70b-versatile", temperature=0)
# llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
# llm = ChatGroq(model_name="llama3-groq-70b-8192-tool-use-preview", temperature=0)
# llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)
# llm = ChatTogether(model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", temperature=0)
# llm = ChatFireworks(
#     model="accounts/fireworks/models/llama-v3p1-70b-instruct", temperature=0
# )
llm = ChatTogether(model="deepseek-ai/DeepSeek-V3", temperature=0)
llm_4o_mini = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)

# jina_embeddings = JinaEmbeddings(model="jina-embeddings-v3-large")
# vectorstore = PineconeVectorStore(
#     embedding=jina_embeddings, index_name="informasi-umum-itb-jina"
# )

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
vectorstore = PineconeVectorStore(embedding=embeddings, index_name="informasi-umum-itb")
# db = SQLDatabase.from_uri(os.getenv("SUPABASE_URI"))
