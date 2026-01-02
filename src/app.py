import streamlit as st
import chromadb
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from pathlib import Path
from dotenv import load_dotenv
import os

# 1. Configuration & Setup
load_dotenv()

st.set_page_config(page_title="Comcast CX Intelligence", page_icon="📡", layout="wide")

# Custom CSS for a professional look
st.markdown(
    """
<style>
    .stChatMessage {font-family: 'Inter', sans-serif;}
    .reportview-container {background: #0e1117;}
    h1 {color: #FF4B4B;}
    .source-box {
        background-color: #262730;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 3px solid #FF4B4B;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 2. Connect to the "Brain" (ChromaDB)
# We assume the script runs from the project root or src,
# but the DB is in the root folder 'chroma_db_data'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "chroma_db_data"


@st.cache_resource
def load_vector_store():
    """
    Connects to the local Vector Store.
    We use the same embedding function name as in the notebook
    to ensure compatibility.
    """
    client = chromadb.PersistentClient(path=DB_PATH)
    # Get the collection we created in the notebook
    collection = client.get_or_create_collection(name="customer_feedback")
    return collection


try:
    collection = load_vector_store()
except Exception as e:
    st.error(f"Error connecting to Vector Store: {e}")
    st.stop()

# 3. Setup the LLM (Gemini)
if "GOOGLE_API_KEY" not in os.environ:
    st.error("Missing GOOGLE_API_KEY in .env file.")
    st.stop()

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0.3,  # Low temperature for factual reporting
    convert_system_message_to_human=True,
)


# 4. Retrieval Function
def get_relevant_context(query, k=5):
    """
    Retrieves the top-k most relevant documents and formats them
    with metadata (Ticket ID, Status) for the LLM.
    """
    results = collection.query(query_texts=[query], n_results=k)

    formatted_docs = []
    sources = []

    if results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            ticket_id = meta.get("ticket_id", "N/A")
            status = meta.get("status", "Unknown")

            # Format for the LLM to understand specifically
            formatted_text = (
                f"[Ticket #{ticket_id} | Status: {status}] Complaint: {doc}"
            )
            formatted_docs.append(formatted_text)

            # Format for UI display
            sources.append({"id": ticket_id, "status": status, "text": doc})

    return "\n\n".join(formatted_docs), sources


# 5. UI Layout
st.title("📡 Comcast Customer Intelligence (RAG)")
st.caption("AI-Powered Semantic Search & Insights on Real Customer Complaints")

# Sidebar for controls
with st.sidebar:
    st.header("⚙️ Configuration")
    retrieval_k = st.slider("Documents to Retrieve", min_value=1, max_value=10, value=5)
    st.divider()
    st.info(
        "This system uses RAG (Retrieval-Augmented Generation) to ground answers in real dataset records."
    )

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I have access to the Comcast complaints database. Ask me about specific issues (e.g., 'What are the main billing complaints?').",
        }
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Ask a question about customer feedback..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing complaints database..."):
            # A. Retrieve
            context_text, source_data = get_relevant_context(prompt, k=retrieval_k)

            # B. Augment (Create Prompt)
            # We give the LLM a persona: Senior CX Analyst
            template = """
            You are a Senior Customer Experience (CX) Analyst for Comcast.
            You have access to a database of customer complaints.
            
            Analyze the following retrieved context to answer the user's question.
            
            GUIDELINES:
            1. Base your answer ONLY on the context provided below.
            2. If the context doesn't answer the question, say you don't know based on the available data.
            3. Cite specific Ticket IDs when mentioning examples.
            4. Keep the tone professional, objective, and solution-oriented.
            
            CONTEXT:
            {context}
            
            USER QUESTION:
            {question}
            
            YOUR ANALYSIS:
            """

            prompt_template = PromptTemplate(
                input_variables=["context", "question"], template=template
            )

            # C. Generate
            chain = prompt_template | llm | StrOutputParser()
            response = chain.invoke({"context": context_text, "question": prompt})

            st.markdown(response)

            # D. Show Sources (Transparency)
            with st.expander(f"📚 View {len(source_data)} Source Documents"):
                for source in source_data:
                    st.markdown(
                        f"""
                    <div class="source-box">
                        <b>Ticket #{source["id"]}</b> <span style='color:gray'>({source["status"]})</span><br>
                        <i>"{source["text"][:200]}..."</i>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # Save to history
            st.session_state.messages.append({"role": "assistant", "content": response})
