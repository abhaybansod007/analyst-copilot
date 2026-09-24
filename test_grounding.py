from types import SimpleNamespace
from filing_parser import Filing, Page
from grounding import GroundedAnswer, Citation, Review, ask_filing, validated_citations, retrieve_sources
from langchain_core.documents import Document


def filing():
    return Filing('report.pdf', 'abc', 'pdf', [Page(1, '1', 'Title page'), Page(2, '2', 'Revenue in 2023 was USD 100 million.')], 0, [])

class Store:
    def __init__(self, docs=None):
        self.docs = docs if docs is not None else [Document(page_content=filing().pages[1].text, metadata={'filing_id':'abc','page':2})]
    def similarity_search(self, *args, **kwargs):
        return self.docs

class Model:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0
    def with_structured_output(self, *args, **kwargs):
        return self
    def invoke(self, *args):
        self.calls += 1
        return next(self.responses)


def draft():
    return GroundedAnswer(found=True, answer='Revenue in 2023 was USD 100 million.', citations=[Citation(source_id='S1',quote='Revenue in 2023 was USD 100 million.')])


def test_supported_answer_has_real_pdf_page():
    m = Model([draft(), Review(fully_supported=True,answers_question=True,correct_period_and_units=True)])
    result=ask_filing(Store(),filing(),'What was revenue in 2023?',llm=m)
    assert result['citations'][0]['page']==2
    assert result['citations'][0]['location']=='PDF page 2'
    assert m.calls==2


def test_model_abstention_is_exact():
    m=Model([GroundedAnswer(found=False,answer='Some other text',citations=[])])
    assert ask_filing(Store(),filing(),'What was profit?',llm=m)['answer']=='Not found in this filing'


def test_no_sources_no_model_call():
    m=Model([])
    assert ask_filing(Store([]),filing(),'What was revenue?',llm=m)['answer']=='Not found in this filing'
    assert m.calls==0


def test_fabricated_quote_rejected_before_review():
    d=draft();d.citations[0].quote='Revenue in 2023 was USD 999 million.'
    m=Model([d])
    assert ask_filing(Store(),filing(),'What was revenue?',llm=m)['citations']==[]
    assert m.calls==1


def test_invalid_source_id_rejected():
    d=draft();d.citations[0].source_id='S999'
    assert validated_citations(d,retrieve_sources(Store(),filing(),'revenue')) is None


def test_existing_quote_does_not_prove_wrong_answer():
    d=draft();d.answer='Revenue was USD 999 million.'
    m=Model([d,Review(fully_supported=False,answers_question=True,correct_period_and_units=True)])
    assert ask_filing(Store(),filing(),'What was revenue?',llm=m)['answer']=='Not found in this filing'


def test_foreign_filing_is_excluded():
    foreign=Document(page_content='Revenue 999 million',metadata={'filing_id':'other','page':2})
    assert retrieve_sources(Store([foreign]),filing(),'revenue')=={}


def test_streamlit_empty_state():
    from streamlit.testing.v1 import AppTest
    from pathlib import Path
    app=AppTest.from_file(str(Path(__file__).with_name('app.py'))).run(timeout=20)
    assert not app.exception
