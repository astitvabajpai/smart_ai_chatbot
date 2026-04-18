import json
import os
import time

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

st.set_page_config(page_title="Document Chatbot", layout="wide")
st.title("Document Chatbot")
st.caption("Upload PDFs, index them into ChromaDB, and chat with a Groq-powered RAG system.")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "user" not in st.session_state:
    st.session_state.user = {"id": "default", "email": "default@example.com", "full_name": "Default"}


with st.sidebar:

    st.divider()
    st.header("Upload Documents")
    uploaded_files = st.file_uploader("Select one or more PDFs", type=["pdf"], accept_multiple_files=True)
    if st.button("Index PDFs", use_container_width=True):
        if not uploaded_files:
            st.warning("Choose at least one PDF first.")
        else:
            files = [("files", (file.name, file.getvalue(), "application/pdf")) for file in uploaded_files]
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{API_BASE_URL}/documents/upload",
                    files=files,
                )
                response.raise_for_status()
                payload = response.json()

            job_id = payload.get("job_id")
            st.info(f"Ingestion queued. Job ID: {job_id}")
            if job_id:
                with httpx.Client(timeout=120.0) as client:
                    while True:
                        job_response = client.get(f"{API_BASE_URL}/jobs/{job_id}")
                        job_response.raise_for_status()
                        job = job_response.json()
                        if job["status"] in {"completed", "failed"}:
                            if job["status"] == "completed":
                                chunks = job["result"].get("chunks_indexed", 0)
                                st.success(f"Indexed {chunks} chunks.")
                            else:
                                st.error(f"Ingestion failed: {job['error']}")
                            break
                        time.sleep(1)

    st.divider()
    top_k = st.slider("Top K Chunks", min_value=2, max_value=10, value=5)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                st.json(message["sources"])

prompt = st.chat_input("Ask a question about your documents")

if prompt:

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    history = [
        {"role": message["role"], "content": message["content"]}
        for message in st.session_state.messages[:-1]
    ]

    with st.chat_message("assistant"):
        answer_placeholder = st.empty()
        sources_placeholder = st.empty()
        answer_text = ""
        sources = []

        with httpx.stream(
            "POST",
            f"{API_BASE_URL}/chat/stream",
            json={"question": prompt, "chat_history": history, "top_k": top_k},
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload == '"completed"':
                        continue
                    parsed = json.loads(payload)
                    if isinstance(parsed, dict) and "sources" in parsed:
                        sources = parsed["sources"]
                    elif isinstance(parsed, str):
                        answer_text += parsed
                        answer_placeholder.markdown(answer_text)

        if sources:
            with sources_placeholder.expander("Sources"):
                st.json(sources)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer_text,
            "sources": sources,
        }
    )
