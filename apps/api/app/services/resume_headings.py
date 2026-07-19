import re
import unicodedata


def normalize_resume_heading(value: str) -> str:
    """Return a punctuation- and diacritic-insensitive resume heading."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = "".join(
        " " if unicodedata.category(character) == "Pd" or character == "\N{MINUS SIGN}" else character
        for character in normalized
    )
    normalized = "".join(
        character
        for character in unicodedata.normalize("NFKD", normalized)
        if not unicodedata.combining(character)
    )
    return re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE).strip()


def normalized_headings(*values: str) -> frozenset[str]:
    return frozenset(normalize_resume_heading(value) for value in values)


SUMMARY_HEADINGS = normalized_headings(
    # English
    "about",
    "about me",
    "career objective",
    "career summary",
    "executive summary",
    "objective",
    "personal profile",
    "professional profile",
    "professional summary",
    "profile",
    "summary",
    "summary of qualifications",
    # German
    "Berufliches Profil",
    "Berufsziel",
    "Kurzprofil",
    "Persönliches Profil",
    "Profil",
    "Über mich",
    "Zusammenfassung",
    # French
    "À propos",
    "À propos de moi",
    "Objectif professionnel",
    "Profil personnel",
    "Profil professionnel",
    "Résumé professionnel",
)

PERSONAL_HEADINGS = normalized_headings(
    # English
    "contact",
    "contact details",
    "contact information",
    "personal data",
    "personal details",
    "personal information",
    # German
    "Kontakt",
    "Kontaktdaten",
    "Personalien",
    "Persönliche Angaben",
    "Persönliche Daten",
    "Persönliche Details",
    "Persönliche Informationen",
    # French
    "Contact",
    "Coordonnées",
    "Coordonnées personnelles",
    "Données personnelles",
    "État civil",
    "Informations personnelles",
    "Informations de contact",
    "Renseignements personnels",
)

SKILL_HEADINGS = normalized_headings(
    # English
    "competencies",
    "computer skills",
    "core competencies",
    "core skills",
    "IT skills",
    "key skills",
    "skills",
    "professional skills",
    "tech stack",
    "technical skills",
    "technical competencies",
    "technical expertise",
    "technical stack",
    "technologies",
    "tools",
    # German
    "EDV-Kenntnisse",
    "Fachkenntnisse",
    "Fähigkeiten",
    "IT-Kenntnisse",
    "IT-Kompetenzen",
    "Kenntnisse",
    "Kernkompetenzen",
    "Kompetenzen",
    "Technische Kenntnisse",
    "Technische Fähigkeiten",
    "Technologien",
    "Werkzeuge",
    # French
    "Aptitudes",
    "Compétences",
    "Compétences informatiques",
    "Compétences clés",
    "Compétences en informatique",
    "Compétences numériques",
    "Compétences professionnelles",
    "Compétences techniques",
    "Informatique",
    "Outils",
    "Savoir-faire",
    "Technologies",
)

EXPERIENCE_HEADINGS = normalized_headings(
    # English
    "career history",
    "employment history",
    "employment experience",
    "experience",
    "professional experience",
    "relevant experience",
    "work experience",
    "work history",
    # German
    "Arbeitserfahrung",
    "Berufliche Erfahrung",
    "Berufliche Erfahrungen",
    "Berufliche Laufbahn",
    "Berufliche Stationen",
    "Beruflicher Werdegang",
    "Berufserfahrung",
    "Berufspraxis",
    "Relevante Erfahrung",
    "Werdegang",
    # French
    "Expérience",
    "Expérience professionnelle",
    "Expériences",
    "Expériences professionnelles",
    "Expérience de travail",
    "Parcours professionnel",
)

PROJECT_HEADINGS = normalized_headings(
    # English
    "project experience",
    "projects",
    "selected projects",
    # German
    "Ausgewählte Projekte",
    "Projekterfahrung",
    "Projekte",
    # French
    "Projets",
    "Projets professionnels",
    "Projets sélectionnés",
)

ACHIEVEMENT_HEADINGS = normalized_headings(
    "accomplishments",
    "achievements",
    "Erfolge",
    "Réalisations",
)

EDUCATION_HEADINGS = normalized_headings(
    # English
    "academic background",
    "academic qualifications",
    "education",
    "education and certifications",
    "education certifications",
    "education and training",
    "educational background",
    "qualifications",
    "training",
    # German
    "Akademische Ausbildung",
    "Akademischer Werdegang",
    "Aus- und Weiterbildung",
    "Ausbildung",
    "Bildung",
    "Bildungsweg",
    "Schulbildung",
    "Studium",
    # French
    "Études",
    "Diplômes et formations",
    "Formation",
    "Formation académique",
    "Formation et diplômes",
    "Formations",
    "Parcours académique",
    "Parcours scolaire",
)

CERTIFICATION_HEADINGS = normalized_headings(
    # English
    "certificates",
    "certifications",
    "certifications and training",
    "courses",
    "professional development",
    # German
    "Weiterbildungen",
    "Zertifikate",
    "Zertifizierungen",
    # French
    "Certificats",
    "Certifications",
    "Certificats et formations",
    "Formation continue",
)

LANGUAGE_HEADINGS = normalized_headings(
    "language skills",
    "languages",
    "foreign languages",
    "Fremdsprachen",
    "Sprachen",
    "Sprachkenntnisse",
    "Compétences linguistiques",
    "Langues",
    "Langues étrangères",
)

OTHER_HEADINGS = normalized_headings(
    "hobbies",
    "interests",
    "references",
    "Hobbys",
    "Interessen",
    "Referenzen",
    "Centres d'intérêt",
    "Intérêts",
    "Références",
)

ALL_RESUME_HEADINGS = frozenset().union(
    SUMMARY_HEADINGS,
    PERSONAL_HEADINGS,
    SKILL_HEADINGS,
    EXPERIENCE_HEADINGS,
    PROJECT_HEADINGS,
    ACHIEVEMENT_HEADINGS,
    EDUCATION_HEADINGS,
    CERTIFICATION_HEADINGS,
    LANGUAGE_HEADINGS,
    OTHER_HEADINGS,
)
