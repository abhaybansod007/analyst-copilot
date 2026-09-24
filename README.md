# Grounded replacement for your Streamlit app

This version keeps ChatOpenAI, OpenAIEmbeddings, RecursiveCharacterTextSplitter and InMemoryVectorStore, while enforcing retrieval before every answer. It supports PDF and HTML uploads.

## Run

Use Python 3.11 or 3.12:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Copy `.env.example` to `.env` and set OPENAI_API_KEY, or enter your key in the app's sidebar. The API-key field is hidden when a non-empty key is already configured through `.env` or the server environment. Missing or whitespace-only values show the password input. Never commit the actual `.env` file. Upload files, click Process selected files, select the filing, then click Build search index. Building embeddings and asking questions use your OpenAI API credits.

## What changed from your code

1. Retrieval happens in Python before each model call. An autonomous agent cannot decide to skip it.
2. The prompt asks for an answer or abstention, rather than reviewing a nonexistent proposed answer.
3. The model returns a structured `found`, `answer`, and `citations` object.
4. Python rejects missing citations, unknown source IDs, and quotes that do not match the retrieved text.
5. A second model call checks whether the cited text actually supports the answer, including financial year, units and scope.
6. The application displays exactly `Not found in this filing` when evidence is missing or validation rejects the answer.
7. Filename and source page are attached by Python, never taken from a model-generated page number. Expand a citation to inspect its quote and full source page.
8. Only the current upload batch is loaded. Multiple uploaded files are separately selectable, so answers are scoped to one filing.
9. File bytes are parsed directly; there is no shared `docs_files` directory to pick up stale reports or require filename-based writes.
10. The uploader actually accepts PDFs, and session-state keys are consistently named.

Use `from langchain_core.vectorstores import InMemoryVectorStore` in current LangChain. The unused Groq, agent, tools and checkpoint imports were removed from this focused version. Questions are independent; no previous answer is treated as evidence. The earlier LangGraph project can be used if you also need follow-up memory.

## PDF versus HTML pages

PDF citations use the actual one-based physical PDF page index. The PDF's printed page label may differ. HTML does not have a fixed PDF page number: SEC page-break segments and detected printed footer labels are displayed separately. A plain HTML file without page breaks is one segment. To supply actual PDF page numbers for an HTML filing, upload the corresponding PDF; never invent a page number from its chunk index.

## Why a prompt alone is insufficient

Similarity search returns nearest passages even when none answers the question. A high similarity score is not proof. This code uses structured abstention, exact quote verification and a separate semantic review. No universal similarity threshold is assumed. Tune retrieval and evaluate wrong answers and abstentions on your own questions.

These checks reduce unsupported answers but do not guarantee zero hallucinations. A matching quotation does not by itself prove the answer, and the reviewer can also make mistakes. Financial calculations receive model review here, not a deterministic arithmetic engine; the earlier Analyst Copilot project includes additional arithmetic validation. A retrieval miss can cause abstention even when the answer exists elsewhere in the filing. Scanned PDFs need OCR before upload.

API/network/billing errors are shown as errors, never mislabeled as evidence that a filing has no answer. This local app is not configured for public multi-user hosting. Extracted filings and vector stores stay in the current Streamlit session; indexing sends extracted text to OpenAI and answering sends retrieved pages. LangSmith tracing is disabled around answer calls.

## Validation

Eight local tests check grounded acceptance, physical PDF page assignment, exact abstention text, forged quotes/IDs, reviewer rejection, document isolation and Streamlit startup. Model calls are mocked in tests. Live OpenAI behavior remains untested without an API key.

```bash
python -m pip install pytest
python -m pytest -q
```

Structured model output is implemented using ChatOpenAI's documented `with_structured_output` API: https://docs.langchain.com/oss/python/integrations/chat/openai
