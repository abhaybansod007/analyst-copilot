
# 📑 The Analyst Copilot

A document chatbot that answers questions from uploaded financial filings and provides source evidence for verification.

🚀 **Live demo:** [Try The Analyst Copilot](https://analyst-copilot-by-abhaybansod.streamlit.app/)

## Technology Stack

| Component | Technology / Tool | Purpose |
|---|---|---|
| Language | Python | Application logic and document processing |
| User interface | Streamlit | File uploads, chat interface, and evidence display |
| LLM provider | OpenAI | Answer generation and evidence review |
| Chat integration | LangChain `ChatOpenAI` | Connects the application to the language model |
| Embeddings | `OpenAIEmbeddings` — `text-embedding-3-small` | Converts document text into searchable vectors |
| Vector store | LangChain `InMemoryVectorStore` | Stores and searches document embeddings within the session |
| Text splitting | `RecursiveCharacterTextSplitter` | Divides documents into overlapping chunks |
| PDF parsing | pypdf | Extracts text and preserves PDF page references |
| HTML parsing | lxml | Extracts filing text and table content |
| Response validation | Pydantic | Defines structured answers, citations, and review results |
| Session management | Streamlit Session State | Maintains uploaded filings, indexes, and chat history |
| Configuration | python-dotenv and Streamlit Secrets | Loads API credentials locally and in deployment |
| Source hosting | GitHub | Stores and versions application code |
| Deployment | Streamlit Community Cloud | Hosts the live application |

## Features

| Feature | Description |
|---|---|
| Document upload | Supports text-based PDF, HTML, and HTM filings |
| Filing selection | Answers questions using the selected uploaded filing |
| Semantic retrieval | Finds passages relevant to the user's question |
| Evidence-based answers | Generates answers from retrieved filing content |
| Abstention | Returns “Not found in this filing” when sufficient supporting evidence is unavailable |
| Source citations | Displays supporting quotations and source locations |
| PDF page references | Shows the physical PDF page number for verification |
| HTML source references | Shows HTML segments and detected printed page labels |
| Evidence inspection | Lets users expand and read the extracted source page |
| Evidence download | Allows downloading the cited page’s extracted text |
| Answer review | Uses a separate model review to check support, relevance, periods, and units |
| API-key configuration | Hides the key input when a key is configured on the server |
| Chat controls | Supports clearing chat history |

## Limitations

- Scanned PDFs require OCR before use.
- HTML segments do not necessarily correspond to PDF pages.
- Uploaded files and indexes are held in session memory and are not persistent.
- Evidence checks reduce unsupported answers but do not guarantee accuracy.
