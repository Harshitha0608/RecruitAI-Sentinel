import pytest
from pathlib import Path
from backend.app.services.jd_parser import JDParser

@pytest.fixture
def failing_jd_file(tmp_path: Path) -> Path:
    jd_content = """# Role SFDC CRM- 5+Yrs

Location Bangalore

Who are we looking for?
Technical Salesforce developer with experience in complex software development and support...

Yrs of experience
Must have at least 5 to 8 Years of SFDC development and implementation experience

Technical Skills

Must have

Primary Skills:
Salesforce Service Cloud Sales Cloud
Salesforce CRM/PRM Modules.
Salesforce Apex, Visualforce, Flows, Triggers, fields, page layouts, record types, custom settings, dashboards and reports
Lightning Aura, LWC, HTML, CSS, JavaScript
Integration SOAP, REST, Bulk API), integration patterns, and best practices.
Knowledge of Omniscripts is an added advantage.
Knowledge of SFDC configuration including use of data loader, Salesforce for Outlook, and other third-party tools
Experience with Interactive client-side single page applications

Secondary Skills:
Familiarity with CI/CD tools (e.g., Jenkins, Copado) and version control systems (e.g., Git)
Salesforce certifications (e.g., Platform Developer I/II, App Builder) are a strong plus

Key Responsibilities
Develop and maintain Salesforce applications using Apex, Visualforce, and Lightning Web Components (LWC).
Customize Salesforce environments to meet business requirements, including creating custom objects, fields, workflows, and process builders.
Integrate Salesforce with other systems using REST/SOAP APIs and middleware.
Collaborate with stakeholders to gather requirements and translate them into technical specifications.
Troubleshoot and resolve technical issues within the Salesforce platform.

Education qualification
BE/B.Tech/MCA/M.Tech

Certifications
Salesforce Developer Certification
"""
    jd_path = tmp_path / "failing_jd.txt"
    jd_path.write_text(jd_content, encoding="utf-8")
    return jd_path

def test_failing_jd_regression(failing_jd_file):
    parser = JDParser(file_path=str(failing_jd_file))
    jd = parser.parse()

    # Title separated from 5+Yrs suffix
    assert jd.title.strip() == "SFDC CRM", f"Expected 'SFDC CRM', got '{jd.title}'"

    # Location = Bangalore
    assert jd.location.strip() == "Bangalore"

    # Min/Max experience
    assert jd.experience_requirement.min_years == 5.0
    assert jd.experience_requirement.max_years == 8.0

    # Education populated from explicit section
    assert "BE/B. Tech/MCA/M. Tech" in jd.education

    # Responsibilities contain ONLY responsibility statements
    responsibilities = "\n".join(jd.responsibilities)
    assert "Develop and maintain Salesforce applications" in responsibilities
    assert "BE/B.Tech" not in responsibilities
    assert "Salesforce Developer Certification" not in responsibilities

    # Robust negative assertions: certification fragments and structural noise must NOT leak into skills
    all_skill_lists = (
        jd.requirements + jd.preferred_skills + jd.technical_skills +
        jd.programming_languages + jd.frameworks + jd.libraries + jd.nice_to_have
    )
    all_skills_lower = [s.lower().strip() for s in all_skill_lists]

    forbidden_exact = [
        "salesforce certifications (e. g.",
        "salesforce certifications (e.g.",
        "platform developer i/ii",
        "app builder) are a strong plus",
        "i", "ii", "iii", "i/ii", "1/2", "pd1", "pd2",
        "must", "primary", "secondary", "preferred"
    ]
    for forbidden in forbidden_exact:
        assert forbidden not in all_skills_lower, f"Forbidden certification/structural item '{forbidden}' leaked into skills!"

    # Actual Salesforce/technical skills are extracted
    assert any("Salesforce" in s for s in jd.technical_skills + jd.requirements)
    assert any("LWC" in s or "Lightning" in s for s in jd.technical_skills + jd.requirements)
    assert "JavaScript" in jd.programming_languages or "JavaScript" in jd.technical_skills

    # Certifications extracted properly (both explicit section and inline secondary section)
    cert_str = " ".join(jd.certifications).lower()
    assert "salesforce developer certification" in cert_str
    assert "platform developer" in cert_str
    assert "app builder" in cert_str

    # Not specified is not fabricated when corresponding information exists
    assert jd.title != "Not specified"
    assert jd.location != "Not specified"
    assert jd.education != "Not specified"


def test_canonical_sfdc_crm_baseline():
    """Validates the canonical SFDC CRM job description baseline structure, counts, and representative content."""
    sfdc_path = Path(__file__).resolve().parents[1] / "app" / "active_job_description.txt"
    assert sfdc_path.exists(), f"Canonical SFDC JD missing: {sfdc_path}"

    parser = JDParser(file_path=str(sfdc_path))
    jd = parser.parse()

    # 1. Header and Core Metadata
    assert jd.title == "SFDC CRM", f"Expected title 'SFDC CRM', got '{jd.title}'"
    assert jd.location == "Bangalore", f"Expected location 'Bangalore', got '{jd.location}'"
    assert jd.experience_requirement.min_years == 5.0, f"Expected min_years 5.0, got {jd.experience_requirement.min_years}"
    assert jd.experience_requirement.max_years == 8.0, f"Expected max_years 8.0, got {jd.experience_requirement.max_years}"
    assert jd.education != "Not specified"
    assert "Bachelor" in jd.education or "degree" in jd.education

    # 2. Approved Canonical Structural Counts
    assert len(jd.requirements) == 11, f"Expected 11 requirements, got {len(jd.requirements)}: {jd.requirements}"
    assert len(jd.preferred_skills) == 5, f"Expected 5 preferred skills, got {len(jd.preferred_skills)}: {jd.preferred_skills}"
    assert len(jd.certifications) == 5, f"Expected 5 certifications, got {len(jd.certifications)}: {jd.certifications}"
    assert len(jd.responsibilities) == 8, f"Expected 8 responsibilities, got {len(jd.responsibilities)}: {jd.responsibilities}"

    # 3. Representative Requirements Content
    assert any("Salesforce Service Cloud Sales Cloud" in r for r in jd.requirements), "Missing Salesforce Service Cloud / Sales Cloud"
    assert any("Salesforce CRM/PRM Modules" in r for r in jd.requirements), "Missing Salesforce CRM/PRM Modules"
    assert any("Apex" in r and "Visualforce" in r and "Flows" in r and "Triggers" in r for r in jd.requirements), "Missing Apex/Visualforce/Flows/Triggers"
    assert any("Lightning" in r and "LWC" in r and "JavaScript" in r for r in jd.requirements), "Missing Lightning/LWC/JavaScript"
    assert any("SOAP" in r and "REST" in r and "Bulk API" in r for r in jd.requirements), "Missing SOAP/REST/Bulk API"
    assert "GitHub" in jd.requirements, "Missing GitHub in requirements"

    # 4. Representative Preferred Skills Content
    assert "MSSQL DB" in jd.preferred_skills, "Missing MSSQL DB in preferred skills"
    assert "NodeJS" in jd.preferred_skills, "Missing NodeJS in preferred skills"
    assert "Managed package experience" in jd.preferred_skills, "Missing Managed package experience in preferred skills"
    assert any("Einstein Analytics" in p and "Community Cloud" in p for p in jd.preferred_skills), "Missing Einstein Analytics/Community Cloud"
    assert any("PD1" in p for p in jd.preferred_skills), "Missing PD1 certification in preferred skills"

    # 5. Representative Certifications Content
    assert any("Salesforce Administrator" in c for c in jd.certifications), "Missing Salesforce Administrator in certifications"
    assert any("ADM-201" in c for c in jd.certifications), "Missing ADM-201 in certifications"
    assert any("Platform App Builder" in c for c in jd.certifications), "Missing Platform App Builder in certifications"
    assert any("Platform Developer I" in c for c in jd.certifications), "Missing Platform Developer I in certifications"
    assert any("PD1" in c for c in jd.certifications), "Missing PD1 in certifications"

    # 6. Responsibilities Content & No Certification Leakage
    responsibilities_text = "\n".join(jd.responsibilities)
    assert "Experience in building Salesforce apps from development to support." in jd.responsibilities
    assert "Good verbal and written communication skills." in jd.responsibilities
    assert not any("Certification" in resp or "ADM-201" in resp or "Platform Developer" in resp for resp in jd.responsibilities), "Certification leaked into responsibilities"
    assert "Education qualification" not in responsibilities_text, "Education header leaked into responsibilities"


def test_explicit_and_inline_certifications_coverage(tmp_path: Path):
    jd_content = """# Senior Salesforce Developer

Location Remote

Technical Skills
Salesforce Apex, LWC, Visualforce
Good to have PD1 certification

Secondary Skills
Salesforce certifications (e.g., Platform Developer I/II, App Builder) are a strong plus

Certifications
Salesforce Administrator (ADM-201)
Salesforce Platform App Builder
Salesforce Platform Developer I
"""
    jd_file = tmp_path / "cert_jd.txt"
    jd_file.write_text(jd_content, encoding="utf-8")

    parser = JDParser(file_path=str(jd_file))
    jd = parser.parse()

    # 1. Certifications are represented in the certifications field
    certs_lower = [c.lower() for c in jd.certifications]
    assert any("administrator" in c or "adm-201" in c for c in certs_lower)
    assert any("platform app builder" in c or "app builder" in c for c in certs_lower)
    assert any("platform developer" in c for c in certs_lower)
    assert any("pd1" in c for c in certs_lower)

    # 2. Certification phrases do NOT leak into ordinary skill lists
    skill_items = [s.lower().strip() for s in (jd.requirements + jd.preferred_skills + jd.technical_skills + jd.nice_to_have)]

    forbidden_items = [
        "salesforce certifications (e. g.",
        "salesforce certifications (e.g.",
        "app builder) are a strong plus",
        "good to have pd1 certification",
        "must", "primary", "secondary"
    ]
    for forbidden in forbidden_items:
        assert forbidden not in skill_items, f"Forbidden item '{forbidden}' leaked into skills!"

    # 3. Genuine Salesforce technical skills remain present
    assert any("apex" in s.lower() for s in jd.technical_skills + jd.requirements)
    assert any("lwc" in s.lower() for s in jd.technical_skills + jd.requirements)


def test_inline_section_content_extraction(tmp_path: Path):
    jd_content = """# Senior Software Engineer

Requirements: Python, FastAPI, React, Docker

Preferred Skills: Python, SQL

Responsibilities:
Build AI-powered screening systems.
Maintain backend services.

Education: BS Computer Science
"""
    jd_file = tmp_path / "inline_jd.txt"
    jd_file.write_text(jd_content, encoding="utf-8")

    parser = JDParser(file_path=str(jd_file))
    jd = parser.parse()

    reqs_str = " ".join(jd.requirements)
    assert "Python" in reqs_str and "FastAPI" in reqs_str and "React" in reqs_str and "Docker" in reqs_str

    pref_str = " ".join(jd.preferred_skills)
    assert "Python" in pref_str and "SQL" in pref_str


def test_inline_section_edge_cases():
    # 1. Requirements: Python, FastAPI, React, Docker
    jd_content_1 = "Requirements: Python, FastAPI, React, Docker\n"
    parser1 = JDParser()
    parser1.raw_content = parser1._preprocess_raw_content(jd_content_1)
    reqs1 = parser1.extract_requirements()
    assert len(reqs1) == 1
    assert "Python, FastAPI, React, Docker" in reqs1[0]

    # 2. Skills: Python, SQL
    jd_content_2 = "Skills: Python, SQL\n"
    parser2 = JDParser()
    parser2.raw_content = parser2._preprocess_raw_content(jd_content_2)
    reqs2 = parser2.extract_requirements()
    assert len(reqs2) == 1
    assert "Python, SQL" in reqs2[0]

    # 3. Multiline section immediately following an inline section
    jd_content_3 = "Requirements: Python, FastAPI\nMust have 3 years experience\nStrong analytical skills\nEducation: BS CS\n"
    parser3 = JDParser()
    parser3.raw_content = parser3._preprocess_raw_content(jd_content_3)
    reqs3 = parser3.extract_requirements()
    assert len(reqs3) == 3
    assert "Python, FastAPI" in reqs3[0]
    assert "Must have 3 years experience" in reqs3[1]
    assert "Strong analytical skills" in reqs3[2]

    # 4. Empty inline section such as "Requirements:" remains empty
    jd_content_4 = "Requirements:\n"
    parser4 = JDParser()
    parser4.raw_content = parser4._preprocess_raw_content(jd_content_4)
    reqs4 = parser4.extract_requirements()
    assert len(reqs4) == 0


def test_sample_jd_txt_boundary_regression():
    sample_jd_path = Path(__file__).resolve().parents[2] / "sample_jd.txt"
    assert sample_jd_path.exists(), "sample_jd.txt fixture must exist"

    parser = JDParser(file_path=str(sample_jd_path))
    jd = parser.parse()

    # 1. Role Overview / responsibilities does not consume Technical Requirements
    summary_and_resp = (jd.summary or "") + " " + " ".join(jd.responsibilities)
    assert "Technical Requirements" not in summary_and_resp
    assert "Docker & Kubernetes" not in summary_and_resp

    # 2. Technical requirements are extracted as requirements/skills
    all_reqs = jd.requirements + jd.technical_skills
    assert any("Python" in s for s in all_reqs)
    assert any("FastAPI" in s for s in all_reqs)
    assert any("Docker" in s for s in all_reqs)

    # 3. Education content is not turned into skills
    all_skills = jd.requirements + jd.preferred_skills + jd.technical_skills
    skills_str = " ".join(all_skills).lower()
    assert "bachelor's degree" not in skills_str
    assert "computer science or related field" not in skills_str
    assert "bachelor" in jd.education.lower() or "computer science" in jd.education.lower()

    # 4. Word-by-word fallback not triggered for Technical Requirements
    assert len(jd.requirements) > 0


def test_camelcase_and_branded_terms_preservation():
    """Verifies that OpenAI, QLoRA, DocuSign, and normal prose are not corrupted by naive lowercase-uppercase splitting."""
    parser = JDParser()

    # 1. Targeted technical and brand names
    text_brands = "We build AI systems using OpenAI API, QLoRA fine-tuning, and DocuSign e-signatures."
    preprocessed_brands = parser._preprocess_raw_content(text_brands)
    assert "OpenAI" in preprocessed_brands
    assert "Open\nAI" not in preprocessed_brands
    assert "QLoRA" in preprocessed_brands
    assert "QLo\nRA" not in preprocessed_brands
    assert "DocuSign" in preprocessed_brands
    assert "Docu\nSign" not in preprocessed_brands

    # 2. Normal prose and words with mixed-case / substrings
    prose = "We offer relocation assistance to Bangalore. Our developers build high-throughput applications."
    preprocessed_prose = parser._preprocess_raw_content(prose)
    assert "relocation assistance" in preprocessed_prose
    assert "re\nlocation" not in preprocessed_prose
    assert "high-throughput" in preprocessed_prose


def test_squashed_section_and_experience_boundary_preprocessing():
    """Verifies that squashed section headers and experience boundaries are safely separated."""
    parser = JDParser()

    # Squashed headers
    assert "developer\nTechnical Skills: Python" in parser._preprocess_raw_content("developerTechnical Skills: Python")
    assert "Bangalore\nLocation Bangalore" in parser._preprocess_raw_content("BangaloreLocation Bangalore")
    assert "support\nWho are we looking for? A developer" in parser._preprocess_raw_content("supportWho are we looking for? A developer")
    assert "developer\nPrimary Skills: Salesforce" in parser._preprocess_raw_content("developerPrimary Skills: Salesforce")
    assert "developer\nSecondary Skills: Git" in parser._preprocess_raw_content("developerSecondary Skills: Git")
    assert "developer\nKey Responsibilities Develop code" in parser._preprocess_raw_content("developerKey Responsibilities Develop code")
    assert "developer\nEducation qualification BE/B. Tech" in parser._preprocess_raw_content("developerEducation qualification BE/B.Tech")
    assert "Certified\nCertifications Salesforce" in parser._preprocess_raw_content("CertifiedCertifications Salesforce")

    # Squashed experience boundaries
    assert "developer\n5+ Years experience" in parser._preprocess_raw_content("developer5+ Years experience")
    assert "experience\n5 to 8 Years of SFDC" in parser._preprocess_raw_content("experience5 to 8 Years of SFDC")


def test_jd_parser_full_model_with_brand_names(tmp_path: Path):
    """End-to-end parse test confirming OpenAI, QLoRA, and DocuSign are cleanly extracted into JD fields."""
    jd_text = """Job Description: Lead GenAI Architect
Company: Sentinel Technologies
Location: Remote
Employment Type: Full-time
Experience Required: 6-10 years

Role Overview:
Leading frontier Generative AI engineering and agentic workflows.

Required Qualifications:
- Production experience with OpenAI models and API orchestration
- Secure enterprise document signing integration using DocuSign
- Strong Python code quality and system architecture

Preferred Skills:
- Parameter-efficient fine-tuning using QLoRA and LoRA
- Experience with vector databases and semantic search

Key Responsibilities:
- Design and deploy scalable LLM solutions.
- Integrate third-party vendor APIs including OpenAI and DocuSign.

Education:
B.Tech or M.Tech in Computer Science
"""
    jd_file = tmp_path / "genai_jd.txt"
    jd_file.write_text(jd_text, encoding="utf-8")

    parser = JDParser(file_path=str(jd_file))
    jd = parser.parse()

    assert jd.title == "Lead GenAI Architect"
    assert jd.company == "Sentinel Technologies"
    assert jd.location == "Remote"
    assert jd.experience_requirement.min_years == 6.0
    assert jd.experience_requirement.max_years == 10.0

    all_reqs = " ".join(jd.requirements)
    all_prefs = " ".join(jd.preferred_skills)

    # Verify brand names intact without splitting
    assert "OpenAI" in all_reqs
    assert "Open\nAI" not in all_reqs
    assert "DocuSign" in all_reqs
    assert "Docu\nSign" not in all_reqs

    assert "QLoRA" in all_prefs
    assert "QLo\nRA" not in all_prefs


def test_redrob_prose_normalization_and_concept_discovery():
    """Validates conservative semantic normalization on conversational, prose-heavy JDs (Redrob AI)."""
    active_jd_path = Path(__file__).resolve().parents[1] / "app" / "active_job_description.docx"
    assert active_jd_path.exists(), "active_job_description.docx must exist"

    parser = JDParser(file_path=str(active_jd_path))
    jd = parser.parse()

    # 1. Requirements count protected from exploding: exactly 4 core competencies
    assert len(jd.requirements) == 4, f"Expected 4 requirements, got {len(jd.requirements)}: {jd.requirements}"

    req1, req2, req3, req4 = jd.requirements

    # 2. Embedding requirement: concise competency, editorial tail stripped, technologies discoverable
    assert "embeddings-based retrieval systems" in req1.lower()
    assert "we don't care which model" not in req1.lower()
    assert "we care that you've handled" not in req1.lower()
    all_tech = [t.lower() for t in jd.technical_skills]
    assert any("sentence" in t and "transformer" in t for t in all_tech)
    assert any("openai" in t for t in all_tech)
    assert any("bge" in t for t in all_tech)
    assert any("e5" in t for t in all_tech)
    assert "Sentence Transformers" in jd.libraries or "Sentence-Transformers" in jd.libraries
    assert "BGE" in jd.libraries
    assert "E5" in jd.libraries

    # 3. Vector & hybrid search requirement: editorial tail stripped, all named engines discoverable
    assert "vector databases" in req2.lower()
    assert "hybrid search" in req2.lower()
    assert "again, the specific tech doesn't matter" not in req2.lower()
    for engine in ["pinecone", "weaviate", "qdrant", "milvus", "faiss"]:
        assert any(engine in v.lower() for v in jd.vector_databases), f"Missing vector DB: {engine}"
    for db in ["elasticsearch", "opensearch"]:
        assert any(db in d.lower() for d in jd.databases), f"Missing DB: {db}"

    # 4. Python requirement: editorial commentary stripped
    assert "python" in req3.lower()
    assert "yes really" not in req3.lower()
    assert "Python" in jd.programming_languages

    # 5. Ranking evaluation requirement: editorial commentary stripped, metrics discoverable
    assert "ranking systems" in req4.lower()
    assert "if you've never thought" not in req4.lower()
    for metric in ["ndcg", "mrr", "map", "a/b testing"]:
        assert any(metric in t for t in all_tech), f"Missing ranking evaluation metric: {metric}"

    # 6. Preferred skills: exactly 5 competencies, header fragment stripped
    assert len(jd.preferred_skills) == 5, f"Expected 5 preferred skills, got {len(jd.preferred_skills)}: {jd.preferred_skills}"
    pref_text = " ".join(jd.preferred_skills).lower()
    assert "but won't reject you for" not in pref_text
    assert "qlora" in pref_text
    assert "lora" in pref_text
    assert "peft" in pref_text
    assert "xgboost" in pref_text
    assert "distributed systems" in pref_text

    # 7. Disqualifiers: preamble stripped, real criteria retained
    assert len(jd.disqualifiers) == 5, f"Expected 5 disqualifiers, got {len(jd.disqualifiers)}: {jd.disqualifiers}"
    disq_text = " ".join(jd.disqualifiers)
    assert "This is the section most JDs skip" not in disq_text
    assert "Title-chasers" in jd.disqualifiers[0]
    assert "Framework enthusiasts" in jd.disqualifiers[1]

    # 8. Technical skills separation invariant: atomic labels only, no full requirement sentences
    for req in jd.requirements:
        assert req not in jd.technical_skills, f"Full requirement sentence leaked into technical_skills: {req}"
        assert all(t.lower() != req.lower() for t in jd.technical_skills)

    for tech_skill in jd.technical_skills:
        assert len(tech_skill.split()) <= 4, f"Technical skill '{tech_skill}' is too verbose to be atomic"
        assert len(tech_skill) <= 40, f"Technical skill '{tech_skill}' exceeds maximum atomic skill length"
        assert not any(p in tech_skill.lower() for p in ["deployed to", "production experience", "we don't care", "hands-on experience"]), f"Prose leaked into skill: {tech_skill}"

    # Key atomic technologies all discoverable
    expected_atomic = [
        "Sentence Transformers", "OpenAI Embeddings", "BGE", "E5",
        "Pinecone", "Weaviate", "Qdrant", "Milvus", "OpenSearch",
        "Elasticsearch", "FAISS", "Python", "NDCG", "MRR", "MAP",
        "A/B Testing", "LoRA", "QLoRA", "PEFT", "Learning-to-Rank", "XGBoost"
    ]
    tech_skills_lower = [t.lower() for t in jd.technical_skills]
    for exp in expected_atomic:
        assert exp.lower() in tech_skills_lower, f"Expected atomic skill '{exp}' missing from technical_skills"



