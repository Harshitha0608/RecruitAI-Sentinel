import os
import re
import string
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import docx

from backend.app.config.settings import settings
from backend.app.schemas.job_description import JobDescription, ExperienceRequirement

logger = logging.getLogger("app.services.jd_parser")

# Standard English stopwords + generic role terms to filter out during keyword extraction
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "cant", "cannot", "could",
    "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadnt", "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes",
    "her", "here", "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill", "im",
    "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shannt", "she", "shed", "shell", "shes", "should", "shouldnt",
    "so", "some", "such", "than", "that", "thats", "the", "their", "theirs", "them", "themselves", "then", "there",
    "theres", "these", "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve", "werent", "what", "whats",
    "when", "whens", "where", "wheres", "which", "while", "who", "whos", "whom", "why", "whys", "with", "wont",
    "would", "wouldnt", "you", "youd", "youll", "youre", "youve", "your", "yours", "yourself", "yourselves",
    "role", "team", "engineer", "engineering", "company", "candidate", "candidates", "experience", "work", "job",
    "description", "about", "years", "things", "want", "like", "need", "prefer", "preferred", "required", "will",
    "would", "good", "strong", "highly", "build", "design", "development", "developer", "working", "using", "use",
    "first", "days", "weeks", "months", "years", "round", "raised", "raising", "also", "spend", "career",
    "us", "we're", "you'd", "we've", "done", "make", "get", "take", "bring", "highly", "please", "read", "carefully",
    "things", "absolutely", "won't", "reject", "explicitly", "want", "let's", "honest", "different", "differently",
    "most", "bouncing", "between", "early", "stage", "google", "meta", "tcs", "infosys", "wipro", "accenture", "cognizant"
}

# Useless token list to clean recruiter requirements (FIX 2)
MEANINGLESS_TOKENS = {
    "ability", "across", "anchor", "bachelor", "candidate", "candidates", "requirement", "requirements",
    "experience", "experiences", "role", "roles", "team", "teams", "good", "strong", "excellent",
    "understanding", "knowledge", "skills", "working", "work", "job", "position", "company", "companies",
    "organization", "organizations", "developer", "developers", "engineer", "engineers", "specialist",
    "specialists", "analyst", "analysts", "professional", "professionals", "expertise", "expert", "experts",
    "building", "build", "design", "development", "developing", "implementing", "implement", "deploying",
    "deploy", "support", "supporting", "infrastructure", "systems", "system", "environment", "environments",
    "none", "specified", "unknown"
, "must", "primary", "secondary", "preferred", "good", "nice", "have", "domain", "process", "behavioral", "i", "ii", "iii", "i/ii", "1/2", "pd1", "pd2", "certification", "certifications", "certified", "cert", "certs"}
STRUCTURAL_LABELS = {
    "must", "must have", "primary", "primary skills", "secondary", "secondary skills", 
    "preferred", "good to have", "nice to have", "domain skills", "process skills", 
    "behavioral skills", "i", "ii", "iii", "i/ii", "1/2", "pd1", "pd2", "not specified", "none", "unknown", "skills",
    "technical skills", "technical requirements", "technical requirement", "requirements", "responsibilities", "certification", "certifications", "certified", "cert", "certs"
}

# Non-skill document acronyms & business terms that should not be extracted as technical requirements
NON_SKILL_ACRONYMS = {
    "jd", "pm", "hr", "ra", "ndcg", "mrr", "map", "kpi", "kpis", "roi", "sla", "faq",
    "ceo", "cto", "vp", "pr", "ip", "b2b", "b2c", "ncr", "usa", "uk", "eu"
}

# Skill classification ontology
ONTOLOGY = {
    "programming_languages": {
        "python", "c++", "cpp", "go", "golang", "rust", "java", "scala", "kotlin", "c#", "typescript", "javascript", "powershell", "shell", "bash", "ruby", "php", "sql", "perl", "r"
    },
    "frameworks": {
        "fastapi", "django", "flask", "react", "vue", "angular", "next.js", "nextjs", "node.js", "nodejs", "pytorch-lightning", "keras", "tensorflow", "pytorch"
    },
    "libraries": {
        "numpy", "pandas", "scikit-learn", "scikit", "scipy", "transformers", "sentence-transformers", "sentence transformers", "opencv", "bge", "e5", "minilm", "mpnet", "spacy", "nltk", "matplotlib", "seaborn", "xgboost"
    },
    "cloud_platforms": {
        "aws", "amazon web services", "azure", "gcp", "google cloud", "google cloud platform", "heroku", "digitalocean"
    },
    "databases": {
        "elasticsearch", "opensearch", "solr", "postgresql", "postgres", "mysql", "sqlite", "cassandra", "dynamodb", "mongodb", "redis", "neo4j", "mariadb"
    },
    "vector_databases": {
        "faiss", "milvus", "pinecone", "qdrant", "chromadb", "chroma", "weaviate"
    },
    "ai_technologies": {
        "llm", "lora", "qlora", "peft", "rag", "nlp", "bert", "gpt", "openai", "openai embeddings", "embeddings", "vector search", "semantic search", "hybrid search", "ranking systems", "learning-to-rank", "learning to rank", "ndcg", "mrr", "map", "a/b testing", "a/b test", "ab test", "offline-to-online correlation", "distributed training", "distributed systems", "inference optimization", "large-scale inference optimization", "hr-tech", "recruiting tech", "whisper", "wav2vec2", "asr", "deep learning", "machine learning", "computer vision", "recommendation systems", "information retrieval", "recommender systems"
    },
    "soft_skills": {
        "communication", "leadership", "mentoring", "mentor", "collaboration", "teamwork", "problem solving", "time management", "organization", "agile", "scrum"
    },
    "certifications": {
        "ccna", "comptia", "aws certified", "gcp certified", "pmp", "scrum master",
        "salesforce developer certification", "salesforce platform developer i", "salesforce platform developer ii",
        "salesforce platform developer i/ii", "platform developer i/ii", "platform developer i", "platform developer ii",
        "salesforce platform app builder", "platform app builder", "salesforce administrator", "adm-201", "pd1", "pd2", "pd1 certification", "pd2 certification"
    }
}

class JDParser:
    _cached_jd: Optional[JobDescription] = None
    _cached_path: Optional[str] = None
    _cached_mtime: float = 0.0

    def __init__(self, file_path: Optional[str] = None) -> None:
        self.file_path = file_path or settings.JOB_DESCRIPTION_PATH
        self.raw_content = ""
        
        if not self.file_path:
            logger.warning("JDParser init warning: JOB_DESCRIPTION_PATH is not configured.")

    def _preprocess_raw_content(self, text: str) -> str:
        """Splits words mashed together by lowercase-to-uppercase transitions, punctuation issues, and squashed header labels, protecting known tech names."""
        if not text:
            return ""
            
        PROTECTED_TECHS = [
            "Microsoft Entra ID", "Azure Active Directory", "Active Directory",
            "Sentence Transformers", "Sentence-Transformers", "SentenceTransformers", "Google Workspace",
            "Windows/Linux", "TCP/IP", "DNS/DHCP", "PowerShell/Bash", "PowerShell", "Bash",
            "Next.js", "Node.js", "Vue.js", "PyTorch Lightning", "Deep Learning",
            "Machine Learning", "Computer Vision", "Semantic Search", "Recommendation Systems",
            "Information Retrieval", "Recommender Systems", "Distributed Training",
            "GitHub", "GitLab", "CrowdStrike", "CrowdStrike Defender", "TensorFlow", "JavaScript", "TypeScript",
            "MongoDB", "PostgreSQL", "FastAPI", "OpenCV", "PyTorch", "Keras",
            "ChromaDB", "DynamoDB", "CompTIA", "CCNA", "PMP", "Scrum Master", "CI/CD",
            "LoRA", "PEFT", "Natural Language Processing", "NodeJS", "NextJS", "VueJS", "ReactJS", "Salesforce"
        ]
        
        sorted_techs = sorted(PROTECTED_TECHS, key=len, reverse=True)
        placeholders = {}
        for idx, tech in enumerate(sorted_techs):
            placeholder = f"___TECH_{idx}___"
            pattern = re.escape(tech)
            if tech[0].isalnum():
                pattern = r'\b' + pattern
            if tech[-1].isalnum():
                pattern = pattern + r'\b'
            
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            if matches:
                placeholders[placeholder] = tech
                for m in reversed(matches):
                    start, end = m.span()
                    text = text[:start] + placeholder + text[end:]

        text = re.sub(r'([a-zA-Z0-9])\.([A-Z])', r'\1. \2', text)
        text = re.sub(r'([a-zA-Z0-9]):([A-Z])', r'\1: \2', text)
        text = re.sub(r'([a-zA-Z0-9]),([A-Z])', r'\1, \2', text)
        text = re.sub(r'([\)\]\.\?!:])([a-zA-Z])', r'\1 \2', text)

        # Safely split squashed experience boundaries (e.g. "developer5+ Years" -> "developer\n5+ Years")
        text = re.sub(r'(?<=[a-zA-Z])(?=\d+\+?\s*(?:to|-|–|—)?\s*\d*\s*(?:years?|yrs?)\b)', r'\n', text, flags=re.IGNORECASE)

        for placeholder, original in placeholders.items():
            text = text.replace(placeholder, original)

        HEADERS_TO_SPLIT = [
            "Role:", "Job Title:", "Position Title:", "Company:", "Location:", "Employment Type:", "Type:", "Job Type:",
            "Role Overview:", "Role Overview", "Overview:",
            "Key Responsibilities:", "Key Responsibilities", "Responsibilities:",
            "Qualifications & Requirements:", "Qualifications & Requirements",
            "Required Qualifications:", "Required Qualifications",
            "Technical Requirements:", "Technical Requirements",
            "Technical Skills:", "Technical Skills",
            "Education qualification:", "Education qualification", "Education Qualification:", "Education Qualification",
            "Education:",
            "Experience Required:", "Experience:", "Yrs of experience:", "Yrs of experience", "Years of experience:", "Years of experience",
            "Certifications:", "Certifications", "Workplace Skills:", "Key Performance Indicators", "KPIs",
            "Who are we looking for?", "Who are we looking for", "Must have:", "Must have", "Must Have:", "Must Have",
            "Primary Skills:", "Primary Skills", "Secondary Skills:", "Secondary Skills",
            "Preferred Skills:", "Preferred Skills", "Preferred Qualifications:", "Preferred Qualifications",
            "Nice to have:", "Nice to have", "Good to have:", "Good to have",
            "ASR Development:", "Computer Vision:", "Multimodal Fusion:", "Performance Optimization:", "Data Pipelines:", "Evaluation:"
        ]
        sorted_headers = sorted(HEADERS_TO_SPLIT, key=len, reverse=True)
        for header in sorted_headers:
            escaped = re.escape(header)
            if " " in header or header.endswith(":") or "?" in header:
                pattern = r"(?<!\n)(?:\b|(?<=[a-z0-9]))(" + escaped + r")"
                text = re.sub(pattern, r"\n\1", text, flags=re.IGNORECASE)
            else:
                pattern = r"(?<!\n)(?:(?<=[a-z0-9])(" + escaped + r")|(?<=\s)(" + escaped + r")(?=[:\s]|$))"
                text = re.sub(pattern, r"\n\1\2", text)

        # Safely split squashed "Location" header without corrupting words like "relocation"
        text = re.sub(r"(?<!\n)(?<=[a-z0-9])(Location)(?=[:\s]|$)", r"\n\1", text)
            
        return text

    def load(self) -> str:
        """Reads job description from path, supporting .docx and .txt formats."""
        if not self.file_path:
            logger.error("Cannot load Job Description: file_path is not configured.")
            return ""
            
        jd_file = Path(self.file_path)
        if not jd_file.exists():
            logger.error(f"Job Description file does not exist at: {jd_file}")
            return ""
            
        try:
            suffix = jd_file.suffix.lower()
            if suffix == ".docx":
                with open(jd_file, "rb") as f:
                    doc = docx.Document(f)
                    paragraphs = [p.text for p in doc.paragraphs]
                    self.raw_content = "\n".join(paragraphs)
            elif suffix in [".txt", ".md"]:
                with open(jd_file, "r", encoding="utf-8") as f:
                    self.raw_content = f.read()
            else:
                logger.error(f"Unsupported Job Description file format: {suffix}")
                self.raw_content = ""
        except Exception as e:
            logger.error(f"Failed to read Job Description file: {e}")
            self.raw_content = ""
            
        self.raw_content = self._preprocess_raw_content(self.raw_content)
        return self.raw_content

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _is_universal_header(self, line: str, current_section: str = None) -> bool:
        line_clean = re.sub(r'^\s*#+\s*', '', line).strip()
        candidate = line_clean.split(':')[0] if ':' in line_clean else line_clean
        norm = re.sub(r'[^a-zA-Z\s]', '', candidate.lower()).strip()

        headers = {
            "location", "experience", "yrs of experience", "work experience",
            "technical skills", "technical requirements", "technical requirement",
            "skills", "requirements", "required qualifications",
            "responsibilities", "key responsibilities", "duties",
            "education", "education qualification", "academic requirements", "academic",
            "certifications", "certification", "licenses",
            "domain skills", "process skills", "behavioral skills",
            "benefits", "compensation", "salary",
            "about company", "company", "employer"
        }
        if current_section != "skills":
            headers.update({
                "preferred", "good to have", "nice to have", "preferred skills", "preferred qualifications", "secondary skills"
            })
        return norm in headers

    def _clean_bullets(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r"^[•\*\-\d\.\s]+\s*", "", text)
        return text.strip()

    def _clean_editorial_prose(self, text: str) -> str:
        """Strips conversational editorial commentary from requirements without altering the core competency."""
        editorial_patterns = [
            r'\.\s*(?:We don\'t care|We do not care)\b.*$',
            r'[\.\;]\s*(?:Again,?\s+the specific tech doesn\'t matter|Again,?\s+the specific tech does not matter)\b.*$',
            r'\.\s*(?:Yes really,?\s+we care\b.*$)',
            r'\.\s*(?:If you\'ve never|If you have never)\b.*$',
        ]
        cleaned = text.strip()
        for pat in editorial_patterns:
            cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE).strip()
        return cleaned

    def _is_atomic_skill(self, text: str) -> bool:
        """Determines whether text is a concise atomic skill rather than a composite requirement sentence."""
        if not text:
            return False
        clean = text.strip()
        words = clean.split()
        if not (1 <= len(words) <= 3 and 2 <= len(clean) <= 35):
            return False
        if re.search(r'[—–\(\)\.\:\;\?\!\,]', clean):
            return False
        lower = clean.lower()
        if lower in STRUCTURAL_LABELS or lower in STOPWORDS or lower in MEANINGLESS_TOKENS:
            return False
        sentence_indicators = {
            "experience", "production", "hands-on", "familiarity", "knowledge",
            "understanding", "ability", "deployed", "users", "strong", "good",
            "excellent", "demonstrated", "years", "responsibilities", "requirements",
            "advantage", "preferred", "skills", "practices", "patterns", "modules",
            "cloud", "integration"
        }
        if any(w in lower.split() for w in sentence_indicators):
            return False
        return True

    def _extract_section_lines(self, start_pattern: str, end_pattern: str, current_section: str = None) -> List[str]:
        if not self.raw_content:
            return []
            
        lines = self.raw_content.split("\n")
        in_section = False
        section_lines = []
        
        start_re = re.compile(start_pattern, re.IGNORECASE)
        end_re = re.compile(end_pattern, re.IGNORECASE) if end_pattern else None
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            if not in_section:
                m = start_re.search(line_clean)
                if m:
                    in_section = True
                    remainder = line_clean[m.end():].strip()
                    remainder = re.sub(r"^[:\-]\s*", "", remainder).strip()
                    if remainder:
                        section_lines.append(self._clean_bullets(remainder))
                    continue
            elif in_section:
                if end_re and end_re.search(line_clean):
                    break
                if self._is_universal_header(line_clean, current_section):
                    break
                section_lines.append(self._clean_bullets(line_clean))
                
        return section_lines

    def extract_summary(self) -> str:
        """Extracts the professional summary block of the job description."""
        if not self.raw_content:
            return ""
            
        if "raised our Series A round" in self.raw_content:
            lines = self._extract_section_lines(r"^Let's be honest", r"^(What you'd actually be doing|What we mean by)")
            if not lines:
                lines = self._extract_section_lines(r"^Experience Required:", r"^What you'd actually be doing")
                
            paragraphs = []
            for line in lines:
                if not any(line.startswith(p) for p in ["Company:", "Location:", "Employment Type:", "Experience Required:"]):
                    paragraphs.append(line)
            return "\n".join(paragraphs).strip()
            
        overview_match = re.search(r"(?:Role Overview|Overview)(?::|\s)\s*([\s\S]*?)(?:Key Responsibilities|Responsibilities|Qualifications & Requirements|Required Qualifications|Technical Requirements|Technical Skills|Requirements|Skills|Education|$)", self.raw_content, re.IGNORECASE)
        if overview_match:
            overview_text = overview_match.group(1).strip()
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", overview_text) if s.strip()]
            summary_sentences = sentences[:5]
            return " ".join(summary_sentences)
            
        non_empty = [l.strip() for l in self.raw_content.split("\n") if l.strip() and not any(l.strip().startswith(p) for p in ["Role:", "Position Title:", "Location:", "Company:", "Employment Type:", "Experience:"])]
        return " ".join(non_empty[:3])

    def extract_responsibilities(self) -> List[str]:
        """Extracts core duties and tasks."""
        lines = []
        if "Key Responsibilities" in self.raw_content:
            lines = self._extract_section_lines(r"Key Responsibilities", r"Qualifications & Requirements|Required Qualifications")
        if not lines:
            lines = self._extract_section_lines(r"^What you'd actually be doing", r"^(What we mean by|The skills inventory|Things you absolutely need)")
        if not lines:
            lines = self._extract_section_fallback(
                ["Responsibility", "Duty", "What you'll do", "Key Duties", "Role Summary", "Key Responsibilities", "Job Responsibilities"],
                current_section="responsibilities"
            )
        return [self._clean_bullets(line) for line in lines if line.strip()]

    def extract_requirements(self) -> List[str]:
        """Extracts required absolute skills and qualifications."""
        lines = []
        if "Required Qualifications" in self.raw_content:
            lines = self._extract_section_lines(r"Required Qualifications", r"Preferred Qualifications|$", current_section="skills")
        elif "Qualifications & Requirements" in self.raw_content:
            lines = self._extract_section_lines(r"Qualifications & Requirements", r"Key Performance Indicators|KPIs|$", current_section="skills")
        elif "Technical Requirements" in self.raw_content:
            lines = self._extract_section_lines(r"Technical Requirements", r"Preferred Qualifications|Preferred Skills|Education|$", current_section="skills")
        if not lines:
            lines = self._extract_section_lines(r"^Things you absolutely need", r"^(Things we'd like you to have|Things we explicitly do NOT want)", current_section="skills")
        if not lines:
            lines = self._extract_section_fallback(
                ["Required Qualifications", "Qualifications & Requirements", "Technical Requirements", "Required", "Requirement", "Required Skill", "Key Requirement", "Qualification", "What you need", "Skills Required", "Technical Skills", "Skills", "Requirements", "Minimum Qualifications", "Desired Qualifications"],
                stop_headers=["Preferred Qualifications", "Preferred Skills", "Preferred", "Nice to Have", "Desired Skills", "Secondary Skills", "Certifications", "Certification", "Licenses"],
                current_section="skills"
            )
        return [self._clean_bullets(line) for line in lines if line.strip()]

    def extract_preferred_skills(self) -> List[str]:
        """Extracts nice-to-have capabilities and preferences."""
        lines = []
        if "Preferred Qualifications" in self.raw_content:
            lines = self._extract_section_lines(r"Preferred Qualifications", r"Things we explicitly do NOT want|On location|$")
        if not lines:
            lines = self._extract_section_lines(r"^Things we'd like you to have(?:\s*(?:\(|but\s+won't\s+reject\s+you\s+for\)?))?", r"^(Things we explicitly do NOT want|On location)")
        if not lines:
            lines = self._extract_section_fallback(
                ["Preferred Skills", "Preferred", "Nice to Have", "Plusses", "Desired Skills", "Preferred Qualifications", "Secondary Skills"],
                current_section="skills"
            )
        return [self._clean_bullets(line) for line in lines if line.strip()]

    def extract_disqualifiers(self) -> List[str]:
        """Extracts negative criteria or explicit dealbreakers."""
        lines = self._extract_section_lines(r"^Things we explicitly do NOT want", r"^(On location|The vibe check|Final note)")
        disqualifiers = []
        for line in lines:
            cleaned = self._clean_bullets(line)
            if not cleaned:
                continue
            if re.search(r'^(?:this\s+is\s+the\s+section|note:|please\s+note|the\s+following\s+are)\b', cleaned, re.IGNORECASE):
                continue
            disqualifiers.append(cleaned)
        return disqualifiers

    def extract_certifications(self) -> List[str]:
        lines = self._extract_section_fallback(
            ["Certifications", "Certification", "Licenses"],
            current_section="certifications"
        )
        return [self._clean_bullets(line) for line in lines if line.strip()]

    def _parse_certifications_from_text(self, text: str) -> List[str]:
        certs = []
        text_clean = text.strip()

        patterns = [
            (r'\bSalesforce\s+Administrator\s*\([^)]*\)', lambda m: m.group(0)),
            (r'\bADM-\d+\b', lambda m: f"Salesforce Administrator ({m.group(0).upper()})"),
            (r'\b(?:Salesforce\s+)?Platform\s+Developer\s*(?:I/II|1/2)\b', "Salesforce Platform Developer I/II"),
            (r'\b(?:Salesforce\s+)?Platform\s+Developer\s*(?:I|1)\b', "Salesforce Platform Developer I"),
            (r'\b(?:Salesforce\s+)?Platform\s+Developer\s*(?:II|2)\b', "Salesforce Platform Developer II"),
            (r'\b(?:Salesforce\s+)?Platform\s+App\s+Builder\b', "Salesforce Platform App Builder"),
            (r'\bApp\s+Builder\b', "Salesforce Platform App Builder"),
            (r'\bPD1\b', "PD1 Certification"),
            (r'\bPD2\b', "PD2 Certification"),
        ]

        for pattern, cert_name in patterns:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                val = cert_name(match) if callable(cert_name) else cert_name
                if val not in certs:
                    certs.append(val)

        if not certs and re.search(r'\b(?:certifications?|certified)\b', text_clean, re.IGNORECASE):
            cleaned = re.sub(r'^(?:e\.g\.|good to have|nice to have|must have|preferred|\s)+', '', text_clean, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s+(?:are\s+a\s+strong\s+plus|is\s+a\s+plus|preferred|required)\.?$', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'^[•\*\-\d\.\s]+', '', cleaned).strip()
            if cleaned and len(cleaned) <= 80:
                certs.append(cleaned)

        return certs

    def _extract_inline_certifications(self, lines: List[str]) -> Tuple[List[str], List[str]]:
        clean_lines = []
        inline_certs = []

        CERT_SIGNAL_RE = re.compile(
            r'\b(?:certifications?|certified|cert|certs|adm-\d+|pd1|pd2|platform developer\s*(?:i/ii|i|ii|1/2|1|2)?|platform app builder)\b',
            re.IGNORECASE
        )

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            if not CERT_SIGNAL_RE.search(line_str):
                clean_lines.append(line_str)
                continue

            extracted_from_line = self._parse_certifications_from_text(line_str)
            for cert in extracted_from_line:
                if cert not in inline_certs:
                    inline_certs.append(cert)

            chunks = [c.strip() for c in re.split(r'[,|;]', line_str)]
            remaining_skill_chunks = []
            for chunk in chunks:
                if not CERT_SIGNAL_RE.search(chunk):
                    chunk_clean = re.sub(r'^(?:e\.g\.|and|\s)+', '', chunk, flags=re.IGNORECASE).strip()
                    if chunk_clean and not any(phrase in chunk_clean.lower() for phrase in ["strong plus", "added advantage", "nice to have", "good to have"]):
                        remaining_skill_chunks.append(chunk_clean)

            if remaining_skill_chunks:
                clean_lines.append(", ".join(remaining_skill_chunks))

        return clean_lines, inline_certs

    def extract_experience_requirements(self) -> ExperienceRequirement:
        """Parses and returns structured experience boundaries."""
        raw_exp = None
        
        match = re.search(r"^(?:Experience Required|Experience|Work Experience|Min Experience|Min\. Experience|Yrs of experience)(?::|\s)+([^\n]+)$", self.raw_content, re.IGNORECASE | re.MULTILINE)
        if match:
            raw_exp = match.group(1).strip()
        else:
            lines = self.raw_content.split('\n')
            for i, line in enumerate(lines):
                line_clean = re.sub(r'[^a-zA-Z\s]', '', line.lower()).strip()
                if line_clean in ["experience required", "experience", "work experience", "min experience", "yrs of experience"]:
                    if i + 1 < len(lines):
                        val = lines[i+1].strip()
                        if len(val) < 200 and not self._is_universal_header(val):
                            raw_exp = val
                            break
                            
        if not raw_exp:
            title_match = re.search(r"(\d+\+?\s*(?:to|-|–|—)\s*\d+\s*)years?", self.raw_content, re.IGNORECASE)
            if title_match:
                raw_exp = title_match.group(1)
            else:
                title_match2 = re.search(r"(\d+)\+?\s*years?", self.raw_content, re.IGNORECASE)
                if title_match2:
                    raw_exp = title_match2.group(0)
                else:
                    raw_exp = "3+ years"
                    
        min_y = 3.0
        max_y = None
        
        range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to|–|—|and up to)\s*(\d+(?:\.\d+)?)", raw_exp, re.IGNORECASE)
        if range_match:
            min_y = float(range_match.group(1))
            max_y = float(range_match.group(2))
        else:
            single_match = re.search(r"(?:minimum\s+of|minimum|at least|min)?\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:year|yr)", raw_exp, re.IGNORECASE)
            if single_match:
                min_y = float(single_match.group(1))
                max_y = None
                
        return ExperienceRequirement(
            raw_text=raw_exp[:50] if raw_exp else "Not specified",
            min_years=min_y,
            max_years=max_y
        )

    def extract_education(self) -> str:
        """Parses and returns normalized education details."""
        match = re.search(r"^(?:Education qualification|Qualifications - Education|Academic Requirement|Education|Academic)(?::|\s)+([^\n]+)$", self.raw_content, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
            
        lines = self.raw_content.split('\n')
        for i, line in enumerate(lines):
            line_clean = re.sub(r'[^a-zA-Z\s]', '', line.lower()).strip()
            if line_clean in ["education", "education qualification", "academic requirements", "academic"]:
                for next_line in lines[i+1:i+5]:
                    val = next_line.strip()
                    if not val:
                        continue
                    if self._is_universal_header(val):
                        break
                    if len(val) < 250:
                        return val
        return "Not specified"

    def extract_keywords(self) -> List[str]:
        """Extracts clean, normalized, unique technology/framework keywords from raw text."""
        if not self.raw_content:
            return []
            
        COMMON_SKILLS = {
            "python", "fastapi", "django", "flask", "pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas",
            "faiss", "milvus", "pinecone", "qdrant", "chromadb", "elasticsearch", "solr", "redis", "mongodb", "postgresql",
            "mysql", "sqlite", "cassandra", "dynamodb", "neo4j", "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
            "terraform", "ansible", "jenkins", "git", "github", "gitlab", "ci/cd", "graphql", "rest", "grpc", "protobuf",
            "hadoop", "spark", "hive", "kafka", "airflow", "flink", "storm", "java", "scala", "kotlin", "c++", "c#", "go",
            "rust", "typescript", "javascript", "react", "vue", "angular", "next.js", "node.js", "html", "css", "tailwinds",
            "llm", "lora", "peft", "rag", "nlp", "bert", "gpt", "sentence-transformers", "sentence transformers", "transformers", "pytorch-lightning",
            "mlops", "devops", "copilot", "langchain", "llama", "deep learning", "machine learning", "computer vision",
            "natural language processing", "crowdstrike defender",
            "data engineering", "system design", "microservices", "agile", "scrum", "sql", "nosql", "vector database",
            "vector search", "semantic search", "recommendation systems", "information retrieval", "ir", "recommender systems",
            "whisper", "conformer", "wav2vec2", "asr", "distributed training", "cuda", "tensorrt", "microsoft entra id", "active directory",
            "tcp/ip", "dns/dhcp", "powershell/bash", "powershell", "bash", "google workspace", "crowdstrike", "defender", "windows/linux",
            "comptia", "ccna", "pmp", "scrum master"
        }
        
        SKILL_CAPITALIZATION = {
            "python": "Python",
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "pytorch": "PyTorch",
            "tensorflow": "TensorFlow",
            "keras": "Keras",
            "scikit-learn": "Scikit-Learn",
            "numpy": "NumPy",
            "pandas": "Pandas",
            "faiss": "FAISS",
            "milvus": "Milvus",
            "pinecone": "Pinecone",
            "qdrant": "Qdrant",
            "chromadb": "ChromaDB",
            "elasticsearch": "Elasticsearch",
            "solr": "Solr",
            "redis": "Redis",
            "mongodb": "MongoDB",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "sqlite": "SQLite",
            "cassandra": "Cassandra",
            "dynamodb": "DynamoDB",
            "neo4j": "Neo4j",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "k8s": "K8s",
            "aws": "AWS",
            "azure": "Azure",
            "gcp": "GCP",
            "terraform": "Terraform",
            "ansible": "Ansible",
            "jenkins": "Jenkins",
            "git": "Git",
            "github": "GitHub",
            "gitlab": "GitLab",
            "ci/cd": "CI/CD",
            "graphql": "GraphQL",
            "rest": "REST API",
            "grpc": "gRPC",
            "protobuf": "Protobuf",
            "hadoop": "Hadoop",
            "spark": "Spark",
            "hive": "Hive",
            "kafka": "Kafka",
            "airflow": "Airflow",
            "flink": "Flink",
            "storm": "Storm",
            "java": "Java",
            "scala": "Scala",
            "kotlin": "Kotlin",
            "c++": "C++",
            "c#": "C#",
            "go": "Go",
            "rust": "Rust",
            "typescript": "TypeScript",
            "javascript": "JavaScript",
            "react": "React",
            "vue": "Vue",
            "angular": "Angular",
            "next.js": "Next.js",
            "node.js": "Node.js",
            "html": "HTML",
            "css": "CSS",
            "tailwinds": "TailwindCSS",
            "llm": "LLM",
            "lora": "LoRA",
            "peft": "PEFT",
            "rag": "RAG",
            "nlp": "NLP",
            "bert": "BERT",
            "gpt": "GPT",
            "sentence-transformers": "Sentence Transformers",
            "sentence transformers": "Sentence Transformers",
            "transformers": "Transformers",
            "pytorch-lightning": "PyTorch Lightning",
            "mlops": "MLOps",
            "devops": "DevOps",
            "copilot": "Copilot",
            "langchain": "LangChain",
            "llama": "LLaMA",
            "deep learning": "Deep Learning",
            "machine learning": "Machine Learning",
            "computer vision": "Computer Vision",
            "natural language processing": "Natural Language Processing",
            "crowdstrike defender": "CrowdStrike Defender",
            "data engineering": "Data Engineering",
            "system design": "System Design",
            "microservices": "Microservices",
            "agile": "Agile",
            "scrum": "Scrum",
            "sql": "SQL",
            "nosql": "NoSQL",
            "vector database": "Vector Databases",
            "vector search": "Vector Search",
            "semantic search": "Semantic Search",
            "recommendation systems": "Recommendation Systems",
            "information retrieval": "Information Retrieval",
            "ir": "IR",
            "recommender systems": "Recommender Systems",
            "whisper": "Whisper",
            "conformer": "Conformer",
            "wav2vec2": "Wav2Vec2",
            "asr": "ASR",
            "distributed training": "Distributed Training",
            "cuda": "CUDA",
            "tensorrt": "TensorRT",
            "microsoft entra id": "Microsoft Entra ID",
            "active directory": "Active Directory",
            "tcp/ip": "TCP/IP",
            "dns/dhcp": "DNS/DHCP",
            "powershell/bash": "PowerShell/Bash",
            "powershell": "PowerShell",
            "bash": "Bash",
            "google workspace": "Google Workspace",
            "crowdstrike": "CrowdStrike",
            "defender": "Defender",
            "windows/linux": "Windows/Linux",
            "comptia": "CompTIA",
            "ccna": "CCNA",
            "pmp": "PMP",
            "scrum master": "Scrum Master"
        }
        
        if not self.raw_content:
            return []
            
        words = re.findall(r"\b[a-zA-Z0-9\.\-/]+\b", self.raw_content)
        unique_keywords = set()
        
        for w in words:
            w_clean = w.strip().lower()
            w_clean = w_clean.strip(string.punctuation)
            
            if not w_clean or w_clean in STOPWORDS or w_clean in MEANINGLESS_TOKENS or len(w_clean) < 2:
                continue
            if re.match(r"^\d+\.?\d*$", w_clean):
                continue
                
            unique_keywords.add(w_clean)
            
        return sorted(list(unique_keywords))

    def parse_jd(self, file_path: str) -> JobDescription:
        self.file_path = file_path
        self.raw_content = ""
        return self.parse()

    def _extract_section_fallback(self, headers: List[str], stop_headers: List[str] = None, current_section: str = None) -> List[str]:
        if not self.raw_content:
            return []
        lines = self.raw_content.split("\n")
        in_section = False
        section_lines = []
        
        headers_pat = [re.compile(r"^\s*(?:#+\s*)?" + re.escape(h) + r"s?\b", re.IGNORECASE) for h in headers]
        stop_pat = [re.compile(r"^\s*(?:#+\s*)?" + re.escape(sh) + r"s?\b", re.IGNORECASE) for sh in stop_headers] if stop_headers else []
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            if in_section:
                if stop_pat and any(r.search(line_clean) for r in stop_pat):
                    break
                if self._is_universal_header(line_clean, current_section):
                    break
                section_lines.append(self._clean_bullets(line_clean))
            else:
                start_match = None
                for r in headers_pat:
                    m = r.search(line_clean)
                    if m:
                        start_match = m
                        break
                if start_match:
                    in_section = True
                    remainder = line_clean[start_match.end():].strip()
                    remainder = re.sub(r"^[:\-]\s*", "", remainder).strip()
                    if remainder:
                        section_lines.append(self._clean_bullets(remainder))
                    continue
                    
        return [l for l in section_lines if l]

    def generate_recruiter_summary(
        self,
        jd_title: str,
        company: str,
        min_years: Optional[float],
        max_years: Optional[float],
        skills: List[str],
        cloud: List[str],
        databases: List[str],
        vector_dbs: List[str],
        ai_tech: List[str],
        soft_skills: List[str],
        certs: List[str]
    ) -> str:
        """Assembles a highly scannable, recruiter-grade summary block dynamically (FIX 3)."""
        exp_range = f"{int(min_years)}-{int(max_years)}" if (min_years and max_years) else (f"{int(min_years)}+" if min_years else "any")
        
        expertise = []
        if skills:
            expertise.extend(skills[:3])
        if ai_tech:
            expertise.extend(ai_tech[:2])
        if vector_dbs:
            expertise.extend(vector_dbs[:2])
        if databases:
            expertise.extend(databases[:2])
        if cloud:
            expertise.extend(cloud[:2])
            
        expertise_str = ", ".join(list(dict.fromkeys(expertise)))
        
        summary_parts = []
        summary_parts.append(f"This role requires a {jd_title} with {exp_range} years of relevant experience at {company or 'the company'}.")
        if expertise_str:
            summary_parts.append(f"Strong expertise is expected in {expertise_str}.")
        if certs:
            summary_parts.append(f"Preferred certifications include {', '.join(certs)}.")
        if soft_skills:
            summary_parts.append(f"Strong {', '.join(soft_skills[:3])} abilities are desirable.")
            
        return " ".join(summary_parts)

    def parse(self) -> JobDescription:
        if self.file_path:
            p = Path(self.file_path)
            if p.exists():
                mtime = p.stat().st_mtime
                if (JDParser._cached_path == self.file_path and 
                    JDParser._cached_mtime == mtime and 
                    JDParser._cached_jd is not None):
                    return JDParser._cached_jd

        if not self.raw_content:
            self.load()
            
        title = "Not specified"
        company = "Not specified"
        location = "Not specified"
        employment_type = "Not specified"
        
        INVALID_TITLES = {
            "role overview", "overview", "job description", "job title", "title",
            "position title", "position", "role", "key responsibilities", "responsibilities",
            "required qualifications", "preferred qualifications", "education", "experience",
            "technical skills", "workplace skills", "key performance indicators", "kpis",
            "unknown", "not specified"
        }

        title_match = re.search(r"(?:^|\n)#?\s*(?:Job Description|Job Title|Title|Position Title|Position|Role)(?::|\s+-|\s+)*([^\n\r]+)", self.raw_content, re.IGNORECASE)
        if title_match:
            pot_title = title_match.group(1).strip().strip(string.punctuation).strip()
            if pot_title.lower() not in INVALID_TITLES and len(pot_title) < 80:
                title = pot_title

        if title == "Not specified" or title.lower() in INVALID_TITLES:
            lines = [l.strip() for l in self.raw_content.split("\n") if l.strip()]
            for line in lines[:3]:
                line_clean = line.strip(string.punctuation).strip()
                if line_clean.lower() not in INVALID_TITLES and len(line_clean) < 80 and not line_clean.endswith('.'):
                    title = line_clean
                    break

        if title == "Not specified" or title.lower() in INVALID_TITLES:
            patterns = [
                r"\bAs\s+an?\s+([^,\.\n]{3,80})(?:,|\bwill\b|\bto\b|\bfor\b|\bis\b)",
                r"\blooking\s+for\s+an?\s+([^,\.\n]{3,80})(?:,|\bwill\b|\bto\b|\bfor\b|\bwith\b|\bis\b)",
                r"\bseeking\s+an?\s+([^,\.\n]{3,80})(?:,|\bwill\b|\bto\b|\bfor\b|\bwith\b|\bis\b)"
            ]
            for pattern in patterns:
                m = re.search(pattern, self.raw_content, re.IGNORECASE)
                if m:
                    pot_title = m.group(1).strip().strip(string.punctuation).strip()
                    if pot_title.lower() not in INVALID_TITLES and len(pot_title) < 80:
                        pot_title = re.sub(r"^(an?|the)\s+", "", pot_title, flags=re.IGNORECASE)
                        title = pot_title
                        break
                        
        if title == "Not specified" or title.lower() in INVALID_TITLES:
            title = "Not specified"
            
        # Strip experience from title
        title = re.sub(r"(?i)(?:-|\b)\s*\d+\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)(?:\s*of\s*experience)?.*$", "", title).strip(" -:,")
            
        company_match = re.search(r"(?:Company|Organization|Employer):\s*(.*)", self.raw_content, re.IGNORECASE)
        if company_match:
            company = company_match.group(1).strip()
            
        loc_match = re.search(r"^(?:Location|Site|Workplace|City)(?::|\s)+([^\n]+)$", self.raw_content, re.IGNORECASE | re.MULTILINE)
        if not loc_match:
            lines = self.raw_content.split('\n')
            for i, line in enumerate(lines):
                line_clean = re.sub(r'[^a-zA-Z\s]', '', line.lower()).strip()
                if line_clean in ["location", "site", "workplace", "city"]:
                    if i + 1 < len(lines):
                        val = lines[i+1].strip()
                        if len(val) < 50 and not self._is_universal_header(val):
                            location = val
                            break
        if loc_match:
            location = loc_match.group(1).strip()
            if location.lower().startswith("hyderabad"):
                location = "Hyderabad"
            
        emp_match = re.search(r"(?:Employment Type|Type|Job Type|Commitment):\s*(.*)", self.raw_content, re.IGNORECASE)
        if emp_match:
            employment_type = emp_match.group(1).strip()
            
        summary = self.extract_summary()
        requirements = self.extract_requirements()
        preferred_skills = self.extract_preferred_skills()
        responsibilities = self.extract_responsibilities()
        disqualifiers = self.extract_disqualifiers()
        
        if not summary:
            non_empty = [l.strip() for l in self.raw_content.split("\n") if l.strip()]
            summary = "\n".join(non_empty[:3])
            
        if not requirements:
            requirements = self._extract_section_fallback(
                ["Required Qualifications", "Required", "Requirement", "Required Skill", "Key Requirement", "Qualification", "What you need", "Skills Required", "Technical Skills", "Minimum Qualifications", "Desired Qualifications"],
                ["Preferred", "Nice to have", "Responsibility", "Location", "About"]
            )
            
        if not requirements:
            requirements = self.extract_keywords()
            
        if not requirements:
            requirements = self._extract_section_fallback(
                ["Responsibility", "Duty", "What you'll do", "Key Duties", "Role Summary", "Key Responsibilities", "Job Responsibilities"],
                ["Requirement", "Preferred", "Skill"]
            )
            
        if not requirements:
            if summary:
                requirements = [s.strip() for s in summary.split("\n") if s.strip()]
                
        if not requirements:
            if title and title != "unknown":
                requirements = [title]
                
        if not requirements:
            requirements = ["Candidate profile evaluation and vetting."]

        if not preferred_skills:
            preferred_skills = self._extract_section_fallback(
                ["Preferred Skills", "Preferred", "Nice to Have", "Plusses", "Desired Skills", "Preferred Qualifications", "Secondary Skills"],
                current_section="skills"
            )
            
        if not preferred_skills:
            preferred_skills = ["Not specified"]
            
        if not responsibilities:
            responsibilities = self._extract_section_fallback(
                ["Responsibility", "Duty", "What you'll do", "Key Duties", "Role Summary", "Key Responsibilities", "Job Responsibilities"],
                current_section="responsibilities"
            )
            
        extracted_certs = self.extract_certifications()
            
        COMMON_SKILLS = {
            "python", "fastapi", "django", "flask", "pytorch", "tensorflow", "keras", "scikit-learn", "numpy", "pandas",
            "faiss", "milvus", "pinecone", "qdrant", "chromadb", "elasticsearch", "solr", "redis", "mongodb", "postgresql",
            "mysql", "sqlite", "cassandra", "dynamodb", "neo4j", "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
            "terraform", "ansible", "jenkins", "git", "github", "gitlab", "ci/cd", "graphql", "rest", "grpc", "protobuf",
            "hadoop", "spark", "hive", "kafka", "airflow", "flink", "storm", "java", "scala", "kotlin", "c++", "c#", "go",
            "rust", "typescript", "javascript", "react", "vue", "angular", "next.js", "node.js", "html", "css", "tailwinds",
            "llm", "lora", "peft", "rag", "nlp", "bert", "gpt", "sentence-transformers", "sentence transformers", "transformers", "pytorch-lightning",
            "mlops", "devops", "copilot", "langchain", "llama", "deep learning", "machine learning", "computer vision",
            "data engineering", "system design", "microservices", "agile", "scrum", "sql", "nosql", "vector database",
            "vector search", "semantic search", "recommendation systems", "information retrieval", "ir", "recommender systems",
            "whisper", "conformer", "wav2vec2", "asr", "distributed training", "cuda", "tensorrt", "microsoft entra id", "active directory",
            "tcp/ip", "dns/dhcp", "powershell/bash", "powershell", "bash", "google workspace", "crowdstrike", "defender", "windows/linux",
            "comptia", "ccna", "pmp", "scrum master"
        }
        
        SKILL_CAPITALIZATION = {
            "python": "Python",
            "fastapi": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "pytorch": "PyTorch",
            "tensorflow": "TensorFlow",
            "keras": "Keras",
            "scikit-learn": "Scikit-Learn",
            "numpy": "NumPy",
            "pandas": "Pandas",
            "faiss": "FAISS",
            "milvus": "Milvus",
            "pinecone": "Pinecone",
            "qdrant": "Qdrant",
            "chromadb": "ChromaDB",
            "elasticsearch": "Elasticsearch",
            "solr": "Solr",
            "redis": "Redis",
            "mongodb": "MongoDB",
            "postgresql": "PostgreSQL",
            "mysql": "MySQL",
            "sqlite": "SQLite",
            "cassandra": "Cassandra",
            "dynamodb": "DynamoDB",
            "neo4j": "Neo4j",
            "docker": "Docker",
            "kubernetes": "Kubernetes",
            "k8s": "K8s",
            "aws": "AWS",
            "azure": "Azure",
            "gcp": "GCP",
            "terraform": "Terraform",
            "ansible": "Ansible",
            "jenkins": "Jenkins",
            "git": "Git",
            "github": "GitHub",
            "gitlab": "GitLab",
            "ci/cd": "CI/CD",
            "graphql": "GraphQL",
            "rest": "REST API",
            "grpc": "gRPC",
            "protobuf": "Protobuf",
            "hadoop": "Hadoop",
            "spark": "Spark",
            "hive": "Hive",
            "kafka": "Kafka",
            "airflow": "Airflow",
            "flink": "Flink",
            "storm": "Storm",
            "java": "Java",
            "scala": "Scala",
            "kotlin": "Kotlin",
            "c++": "C++",
            "c#": "C#",
            "go": "Go",
            "rust": "Rust",
            "typescript": "TypeScript",
            "javascript": "JavaScript",
            "react": "React",
            "vue": "Vue",
            "angular": "Angular",
            "next.js": "Next.js",
            "node.js": "Node.js",
            "html": "HTML",
            "css": "CSS",
            "tailwinds": "TailwindCSS",
            "llm": "LLM",
            "lora": "LoRA",
            "peft": "PEFT",
            "rag": "RAG",
            "nlp": "NLP",
            "bert": "BERT",
            "gpt": "GPT",
            "sentence-transformers": "Sentence Transformers",
            "sentence transformers": "Sentence Transformers",
            "transformers": "Transformers",
            "pytorch-lightning": "PyTorch Lightning",
            "mlops": "MLOps",
            "devops": "DevOps",
            "copilot": "Copilot",
            "langchain": "LangChain",
            "llama": "LLaMA",
            "deep learning": "Deep Learning",
            "machine learning": "Machine Learning",
            "computer vision": "Computer Vision",
            "data engineering": "Data Engineering",
            "system design": "System Design",
            "microservices": "Microservices",
            "agile": "Agile",
            "scrum": "Scrum",
            "sql": "SQL",
            "nosql": "NoSQL",
            "vector database": "Vector Databases",
            "vector search": "Vector Search",
            "semantic search": "Semantic Search",
            "recommendation systems": "Recommendation Systems",
            "information retrieval": "Information Retrieval",
            "ir": "IR",
            "recommender systems": "Recommender Systems",
            "whisper": "Whisper",
            "conformer": "Conformer",
            "wav2vec2": "Wav2Vec2",
            "asr": "ASR",
            "distributed training": "Distributed Training",
            "cuda": "CUDA",
            "tensorrt": "TensorRT",
            "microsoft entra id": "Microsoft Entra ID",
            "active directory": "Active Directory",
            "tcp/ip": "TCP/IP",
            "dns/dhcp": "DNS/DHCP",
            "powershell/bash": "PowerShell/Bash",
            "powershell": "PowerShell",
            "bash": "Bash",
            "google workspace": "Google Workspace",
            "crowdstrike": "CrowdStrike",
            "defender": "Defender",
            "windows/linux": "Windows/Linux",
            "comptia": "CompTIA",
            "ccna": "CCNA",
            "pmp": "PMP",
            "scrum master": "Scrum Master",
            "qlora": "QLoRA",
            "bge": "BGE",
            "e5": "E5",
            "openai": "OpenAI",
            "openai embeddings": "OpenAI Embeddings",
            "xgboost": "XGBoost",
            "opensearch": "OpenSearch",
            "weaviate": "Weaviate",
            "ndcg": "NDCG",
            "mrr": "MRR",
            "map": "MAP",
            "a/b testing": "A/B Testing",
            "a/b test": "A/B Testing",
            "ab test": "A/B Testing",
            "hybrid search": "Hybrid Search",
            "ranking systems": "Ranking Systems",
            "learning-to-rank": "Learning-to-Rank",
            "learning to rank": "Learning to Rank",
            "distributed systems": "Distributed Systems",
            "inference optimization": "Inference Optimization",
            "large-scale inference optimization": "Large-Scale Inference Optimization",
            "embeddings": "Embeddings",
            "hr-tech": "HR-Tech",
            "recruiting tech": "Recruiting Tech",
            "adm-201": "Salesforce Administrator (ADM-201)",
            "salesforce administrator": "Salesforce Administrator",
            "pd1": "PD1 Certification",
            "pd2": "PD2 Certification",
            "platform app builder": "Salesforce Platform App Builder",
            "platform developer i": "Salesforce Platform Developer I",
            "platform developer ii": "Salesforce Platform Developer II",
            "platform developer i/ii": "Salesforce Platform Developer I/II"
        }

        CERT_SIGNAL_RE = re.compile(
            r'\b(?:certifications?|certified|cert|certs|adm-\d+|pd1|pd2|platform developer\s*(?:i/ii|i|ii|1/2|1|2)?|platform app builder)\b',
            re.IGNORECASE
        )

        HEADER_PREFIX_RE = re.compile(
            r'^\s*(?:#+\s*)?(?:must\s+have|primary\s+skills|secondary\s+skills|technical\s+skills|technical\s+requirements|requirements|preferred\s+skills|preferred\s+qualifications|preferred|good\s+to\s+have|nice\s+to\s+have|skills|key\s+responsibilities|responsibilities|certifications?|education(?:\s+qualification)?)\s*[:\-]\s*',
            re.IGNORECASE
        )

        def _map_atomic_skills(lines: List[str]) -> List[str]:
            extracted = []
            for line in lines:
                line_clean = self._clean_bullets(line)
                line_clean = HEADER_PREFIX_RE.sub('', line_clean).strip()
                line_clean = re.sub(r'^[:\-]\s*', '', line_clean).strip()
                line_clean = line_clean.rstrip(":").strip()
                line_clean = re.sub(r'\.\s*$', '', line_clean).strip()
                
                if not line_clean:
                    continue

                # Strip conversational / editorial commentary while preserving the core competency
                line_clean = self._clean_editorial_prose(line_clean)
                if not line_clean:
                    continue

                line_lower = line_clean.lower()
                if line_lower in STRUCTURAL_LABELS or line_lower in {"must have", "primary skills", "secondary skills", "technical skills", "key responsibilities", "but won't reject you for"}:
                    continue
                if re.match(r"^(?:but\s+won't\s+reject\s+you\s+for|nice\s+to\s+have|plusses|bonus|optional)$", line_lower):
                    continue
                    
                if CERT_SIGNAL_RE.search(line_clean):
                    cleaned_non_cert = re.sub(r'(?:salesforce\s+)?certifications?\s*\([^)]*\)', '', line_clean, flags=re.IGNORECASE)
                    cleaned_non_cert = re.sub(r'\b(?:certifications?|certified|cert|certs|pd1|pd2|platform developer\s*(?:i/ii|i|ii|1/2|1|2)?|platform app builder)\b', '', cleaned_non_cert, flags=re.IGNORECASE).strip()
                    cleaned_non_cert = re.sub(r'^(?:e\.g\.|good to have|nice to have|must have|preferred|\s|,|\(|\))+', '', cleaned_non_cert, flags=re.IGNORECASE).strip()
                    if not cleaned_non_cert or len(cleaned_non_cert) < 2 or cleaned_non_cert.lower() in STRUCTURAL_LABELS:
                        continue
                        
                if 2 <= len(line_clean) <= 300:
                    words = re.findall(r'\b[a-zA-Z0-9\+\#\.\-/]+\b', line_clean)
                    if not all(w.lower() in MEANINGLESS_TOKENS or w.lower() in STOPWORDS for w in words):
                        extracted.append(line_clean)
                        
            return list(dict.fromkeys(extracted))

        clean_req, inline_certs_req = self._extract_inline_certifications(requirements)
        clean_pref, inline_certs_pref = self._extract_inline_certifications(preferred_skills)

        parsed_requirements = _map_atomic_skills(clean_req)
        parsed_preferred = _map_atomic_skills(clean_pref)

        # Deduplicate inline certs and append them back to their respective arrays to preserve source context
        def append_certs_safely(target_list: List[str], certs: List[str]) -> None:
            existing_lower = {s.lower() for s in target_list}
            for c in certs:
                if c.lower() not in existing_lower:
                    target_list.append(c)
                    existing_lower.add(c.lower())

        append_certs_safely(parsed_requirements, inline_certs_req)
        append_certs_safely(parsed_preferred, inline_certs_pref)

        # Process dedicated section certifications
        dedicated_certs = []
        for line in extracted_certs:
            parsed_c = self._parse_certifications_from_text(line)
            if parsed_c:
                for c in parsed_c:
                    if c not in dedicated_certs:
                        dedicated_certs.append(c)
            else:
                clean_l = line.strip()
                if clean_l and clean_l not in dedicated_certs:
                    dedicated_certs.append(clean_l)

        # Route dedicated certs with no explicit mandatory/preferred context deterministically into parsed_requirements
        existing_req_pref_lower = {s.lower() for s in (parsed_requirements + parsed_preferred)}
        for c in dedicated_certs:
            if c.lower() not in existing_req_pref_lower:
                parsed_requirements.append(c)
                existing_req_pref_lower.add(c.lower())

        # Categorize skills into proper ontology groups (FIX 1)
        technical_skills = []
        programming_languages = []
        frameworks = []
        libraries = []
        cloud_platforms = []
        databases = []
        vector_databases = []
        ai_technologies = []
        soft_skills = []
        
        all_certs = list(dict.fromkeys(dedicated_certs + inline_certs_req + inline_certs_pref))
        certifications = list(all_certs)
        nice_to_have = []
        
        category_map = {
            "programming_languages": programming_languages,
            "frameworks": frameworks,
            "libraries": libraries,
            "cloud_platforms": cloud_platforms,
            "databases": databases,
            "vector_databases": vector_databases,
            "ai_technologies": ai_technologies,
            "soft_skills": soft_skills,
            "certifications": certifications,
        }

        all_skills = parsed_requirements + parsed_preferred
        for skill in all_skills:
            skill_lower = skill.lower().strip()
            
            # Semantic synonym mappings
            if skill_lower in ["active directory", "azure active directory", "microsoft entra id"]:
                skill = "Microsoft Entra ID"
                skill_lower = "microsoft entra id"
            if skill_lower == "golang":
                skill = "Go"
                skill_lower = "go"
            if skill_lower == "nextjs":
                skill = "Next.js"
                skill_lower = "next.js"
            if skill_lower == "nodejs":
                skill = "Node.js"
                skill_lower = "node.js"
                
            for category, keyword_set in ONTOLOGY.items():
                target_list = category_map.get(category)
                if skill_lower in keyword_set:
                    matched_kw = SKILL_CAPITALIZATION.get(skill_lower, skill)
                    if target_list is not None and matched_kw not in target_list:
                        target_list.append(matched_kw)
                    if matched_kw not in technical_skills:
                        technical_skills.append(matched_kw)
                else:
                    for kw in sorted(keyword_set, key=len, reverse=True):
                        if len(kw) >= 2 and re.search(r'\b' + re.escape(kw) + r'\b', skill_lower):
                            matched_kw = SKILL_CAPITALIZATION.get(kw, kw.title())
                            if target_list is not None and matched_kw not in target_list:
                                target_list.append(matched_kw)
                            if matched_kw not in technical_skills:
                                technical_skills.append(matched_kw)

            for kw in sorted(COMMON_SKILLS, key=len, reverse=True):
                if len(kw) >= 2 and re.search(r'\b' + re.escape(kw) + r'\b', skill_lower):
                    matched_kw = SKILL_CAPITALIZATION.get(kw, kw.title())
                    if matched_kw not in technical_skills:
                        technical_skills.append(matched_kw)
            
            if skill_lower in [p.lower() for p in parsed_preferred]:
                if skill not in nice_to_have:
                    nice_to_have.append(skill)
            else:
                if self._is_atomic_skill(skill) and skill not in technical_skills:
                    technical_skills.append(skill)

        # Extract Work Mode
        work_mode = "Not specified"
        if re.search(r"\bremote\b", self.raw_content, re.IGNORECASE):
            work_mode = "Remote"
        elif re.search(r"\bhybrid\b", self.raw_content, re.IGNORECASE):
            work_mode = "Hybrid"
        elif re.search(r"\bon-site\b|\bon site\b", self.raw_content, re.IGNORECASE):
            work_mode = "On-site"

        # Extract Relocation
        relocation = "Not specified"
        if re.search(r"\brelocation\b|\brelocate\b", self.raw_content, re.IGNORECASE):
            if re.search(r"\bno relocation\b|\bnot open to relocation\b", self.raw_content, re.IGNORECASE):
                relocation = "No"
            else:
                relocation = "Yes"

        # Extract Notice Preference
        notice_preference = "Not specified"
        notice_match = re.search(r"(?:notice period|notice):\s*([^\n\.]*)", self.raw_content, re.IGNORECASE)
        if notice_match:
            notice_preference = notice_match.group(1).strip()

        # Extract Salary
        salary = "Not specified"
        salary_match = re.search(r"(?:salary|compensation|lpa):\s*([^\n\.]*)", self.raw_content, re.IGNORECASE)
        if salary_match:
            salary = salary_match.group(1).strip()

        exp_req = self.extract_experience_requirements()
        
        # Programmatic recruiter summary (FIX 3)
        summary = self.generate_recruiter_summary(
            jd_title=title,
            company=company,
            min_years=exp_req.min_years,
            max_years=exp_req.max_years,
            skills=parsed_requirements,
            cloud=cloud_platforms,
            databases=databases,
            vector_dbs=vector_databases,
            ai_tech=ai_technologies,
            soft_skills=soft_skills,
            certs=certifications
        )

        # Parser verification checks (FIX 12)
        warnings = []
        if not title or title.strip().lower() in ["not specified", "unknown"]:
            warnings.append("Job Title could not be successfully extracted.")
        if not exp_req or exp_req.min_years is None or exp_req.raw_text.strip().lower() in ["any", "not specified", "unknown"]:
            warnings.append("Experience requirements could not be successfully extracted.")
        
        extracted_edu = self.extract_education()
        if not extracted_edu or extracted_edu.strip().lower() in ["not specified", "unknown"]:
            warnings.append("Education requirements could not be successfully extracted.")
            
        if not parsed_requirements or len(parsed_requirements) == 0:
            warnings.append("Required Skills list could not be successfully extracted.")
            
        if not parsed_preferred or len(parsed_preferred) == 0 or (len(parsed_preferred) == 1 and parsed_preferred[0].strip().lower() in ["not specified", "none", "none specified"]):
            warnings.append("Preferred Skills list could not be successfully extracted.")
            
        if not responsibilities or len(responsibilities) == 0:
            warnings.append("Core Job Responsibilities could not be successfully extracted.")
            
        low_confidence = len(warnings) > 0

        parsed_jd = JobDescription(
            title=title,
            company=company,
            location=location,
            employment_type=employment_type,
            experience_requirement=exp_req,
            education=extracted_edu,
            summary=summary,
            requirements=parsed_requirements if parsed_requirements else requirements,
            preferred_skills=parsed_preferred if parsed_preferred else preferred_skills,
            responsibilities=responsibilities,
            disqualifiers=disqualifiers,
            keywords=self.extract_keywords(),
            technical_skills=technical_skills,
            programming_languages=programming_languages,
            frameworks=frameworks,
            libraries=libraries,
            cloud_platforms=cloud_platforms,
            databases=databases,
            vector_databases=vector_databases,
            ai_technologies=ai_technologies,
            soft_skills=soft_skills,
            certifications=certifications,
            nice_to_have=nice_to_have,
            kpis=self._extract_section_fallback(["KPIs", "KPI", "Metrics", "Evaluation Metrics"], ["Disqualifiers", " Vibe"]),
            work_mode=work_mode,
            relocation=relocation,
            notice_preference=notice_preference,
            salary=salary,
            low_confidence=low_confidence,
            warnings=warnings
        )

        # Cache the parsed result
        if self.file_path:
            p = Path(self.file_path)
            if p.exists():
                JDParser._cached_path = self.file_path
                JDParser._cached_mtime = p.stat().st_mtime
                JDParser._cached_jd = parsed_jd

        return parsed_jd
