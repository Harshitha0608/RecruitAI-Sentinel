import pytest
from pathlib import Path
from backend.app.services.jd_parser import JDParser
from backend.app.config.settings import settings

@pytest.fixture
def mock_jd_file(tmp_path: Path) -> Path:
    jd_content = """Job Description: Senior AI Engineer
Company: Redrob AI
Location: Pune/Noida, India
Employment Type: Full-time
Experience Required: 5–9 years

Let's be honest about this role
We raised our Series A round. We need a coder.

What you'd actually be doing
- Own the intelligence layer matching systems.
- Ship a v2 ranking system.

What we mean by "5-9 years"
We consider strong candidates outside the band.

Things you absolutely need
- Production experience with embeddings-based retrieval systems (sentence-transformers).
- Strong Python code quality.

Things we'd like you to have
- LLM fine-tuning experience (LoRA, PEFT).

Things we explicitly do NOT want
- Title-chasers who switch jobs every year.
- Framework enthusiasts.

On location, comp, and logistics
Location: Noida/Pune hybrid model.
"""
    jd_path = tmp_path / "mock_jd.txt"
    jd_path.write_text(jd_content, encoding="utf-8")
    return jd_path

def test_jd_parser_mock(mock_jd_file):
    parser = JDParser(file_path=str(mock_jd_file))
    parser.load()

    # Test summary extraction
    summary = parser.extract_summary()
    assert "raised our Series A round" in summary

    # Test responsibilities extraction
    responsibilities = parser.extract_responsibilities()
    assert len(responsibilities) == 2
    assert responsibilities[0] == "Own the intelligence layer matching systems."
    assert responsibilities[1] == "Ship a v2 ranking system."

    # Test requirements extraction
    requirements = parser.extract_requirements()
    assert len(requirements) == 2
    assert "embeddings-based retrieval systems" in requirements[0]
    assert requirements[1] == "Strong Python code quality."

    # Test preferred skills extraction
    preferred = parser.extract_preferred_skills()
    assert len(preferred) == 1
    assert "LLM fine-tuning experience" in preferred[0]

    # Test disqualifiers extraction
    disqualifiers = parser.extract_disqualifiers()
    assert len(disqualifiers) == 2
    assert "Title-chasers" in disqualifiers[0]

    # Test experience extraction
    exp = parser.extract_experience_requirements()
    assert exp.raw_text == "5–9 years"
    assert exp.min_years == 5.0
    assert exp.max_years == 9.0

    # Test keywords extraction
    keywords = parser.extract_keywords()
    assert "python" in keywords
    assert "sentence-transformers" in keywords
    assert "lora" in keywords

    # Test parse full model
    jd_model = parser.parse()
    assert jd_model.title == "Senior AI Engineer"
    assert jd_model.company == "Redrob AI"
    assert jd_model.location == "Pune/Noida, India"
    assert jd_model.employment_type == "Full-time"
    assert jd_model.experience_requirement.min_years == 5.0
