from pathlib import Path
import os
import hashlib
import streamlit as st
from dotenv import load_dotenv
from filing_parser import ingest
from grounding import build_store, ask_filing

load_dotenv(Path(__file__).with_name('.env'))
st.set_page_config(page_title='The Analyst Copilot', page_icon='📑')
st.header('The Analyst Copilot')
st.caption('Ask a filing. Inspect the evidence.')

for name, value in {'filings': [], 'messages': [], 'stores': {}, 'selected_id': None}.items():
    if name not in st.session_state:
        st.session_state[name] = value

with st.sidebar:
    key = os.getenv('OPENAI_API_KEY', '').strip()
    if not key:
        try:
            key = str(st.secrets.get('OPENAI_API_KEY', '')).strip()
        except FileNotFoundError:
            # Local runs do not need a Streamlit secrets file.
            key = ''
    if not key:
        key = st.text_input('OpenAI API key', type='password').strip()
    st.caption('Building an index sends extracted filing text to OpenAI for embeddings. Questions and supporting passages are sent for answering. API charges apply.')
    uploaded = st.file_uploader('Select PDF or HTML filings', type=['pdf', 'htm', 'html'], accept_multiple_files=True)
    if st.button('Process selected files', disabled=not uploaded):
        try:
            with st.spinner('Reading selected files…'):
                # Read only this upload batch; no shared directory of old documents.
                filings = [ingest(f.getvalue(), f.name) for f in uploaded]
            st.session_state.filings = filings
            st.session_state.stores = {}
            st.session_state.messages = []
            st.session_state.selected_id = None
            st.rerun()
        except Exception:
            st.error('Could not read a filing. Use an unlocked, text-based PDF or HTML file up to 50 MB. Scanned PDFs need OCR.')

if not st.session_state.filings:
    st.info('Upload and process a filing to begin.')
    st.stop()

filing = st.selectbox('Answer only from this filing', st.session_state.filings,
                      format_func=lambda f: f.name)
if st.session_state.selected_id != filing.digest:
    st.session_state.selected_id = filing.digest
    st.session_state.messages = []

st.caption(f'{len(filing.pages)} source pages / HTML segments')
for warning in filing.warnings:
    st.caption(warning)

# Rebuild with the correct credentials when the key changes; never persist the key.
store_id = filing.digest + hashlib.sha256(key.encode()).hexdigest()
store = st.session_state.stores.get(store_id)
if store is None:
    if key:
        st.info('Build the search index for the selected filing.')
    else:
        st.info('Enter an API key in the sidebar, then build the search index for the selected filing.')
    if st.button('Build search index', disabled=not bool(key)):
        try:
            with st.spinner('Creating embeddings…'):
                store = build_store(filing, key)
            st.session_state.stores[store_id] = store
            st.rerun()
        except Exception:
            st.error('Indexing failed. Check your API key, billing and connection. This is not a “not found” result.')

if st.button('Clear chat'):
    st.session_state.messages = []

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message['role']):
        st.text(message['content'])
        for j, citation in enumerate(message.get('citations', [])):
            with st.expander(f"{citation['document']} · {citation['location']}"):
                st.text(citation['quote'])
                page = filing.pages[citation['page'] - 1]
                st.caption('Full extracted source page / segment')
                st.code(page.text, language=None, wrap_lines=True)
                st.download_button('Download this page text', page.text,
                    file_name=f'page-{page.index}.txt', key=f'page-{i}-{j}')

st.caption('Ask complete questions with the year and metric. Each answer is checked independently against the selected filing.')
question = st.chat_input('Ask about the selected filing', disabled=store is None, max_chars=4000)
if question:
    st.session_state.messages.append({'role': 'user', 'content': question})
    try:
        with st.spinner('Retrieving and checking evidence…'):
            result = ask_filing(store, filing, question, key)
        st.session_state.messages.append({'role': 'assistant', 'content': result['answer'],
                                          'citations': result['citations']})
        st.rerun()
    except Exception:
        st.error('The answer request failed. Check your API key, model access, billing or connection and retry. A service error does not mean the answer is absent.')
