"""
Document loader — loads policy documents from the filesystem or inline definitions.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from rag.core.models import Document, DocType


def load_from_file(
    path: str | Path,
    doc_type: DocType = DocType.OTHER,
    exam_id: str | None = None,
    institution: str | None = None,
    title: str | None = None,
) -> Document:
    """Load a text/markdown file as a Document."""
    p = Path(path)
    content = p.read_text(encoding="utf-8")
    return Document(
        id=str(uuid.uuid4()),
        title=title or p.stem.replace("_", " ").title(),
        content=content,
        doc_type=doc_type,
        exam_id=exam_id,
        institution=institution,
    )


def load_from_directory(
    directory: str | Path,
    doc_type: DocType = DocType.OTHER,
    exam_id: str | None = None,
    institution: str | None = None,
) -> list[Document]:
    """Load all .md and .txt files in a directory."""
    docs = []
    for p in sorted(Path(directory).glob("**/*.md")):
        docs.append(load_from_file(p, doc_type=doc_type, exam_id=exam_id, institution=institution))
    for p in sorted(Path(directory).glob("**/*.txt")):
        docs.append(load_from_file(p, doc_type=doc_type, exam_id=exam_id, institution=institution))
    return docs


# ── Built-in sample documents ─────────────────────────────────────────────────

SAMPLE_EXAM_POLICY = Document(
    id="doc-sample-exam-policy",
    title="Sample Exam Policy",
    doc_type=DocType.EXAM_RULES,
    institution="AI Exam Guardian Demo",
    content="""
# Exam Rules

1. This is a closed-resource examination.
2. Students may not access the internet during the examination.
3. The use of AI assistants is strictly prohibited.
4. Students must remain on the examination page at all times.
5. Copying or pasting text from external sources is prohibited.
6. Opening additional browser tabs or windows is prohibited.
7. The examination must be conducted in a full-screen browser window where possible.
""".strip(),
)

SAMPLE_AI_POLICY = Document(
    id="doc-sample-ai-policy",
    title="AI Assistance Policy",
    doc_type=DocType.AI_POLICY,
    institution="AI Exam Guardian Demo",
    content="""
# AI Assistance Policy

The use of any AI writing assistant, code assistant, or AI-powered tool is strictly
prohibited during examinations. This includes but is not limited to:

- ChatGPT (chat.openai.com)
- Claude (claude.ai)
- Google Gemini (gemini.google.com)
- Microsoft Copilot (copilot.microsoft.com)
- ParakeetAI (parakeet-ai.com)
- Perplexity (perplexity.ai)
- Any other AI-powered content generation tool

Detection of AI-assistant signals combined with behavioral indicators will result in
the session being flagged for teacher review. The teacher makes the final determination.
No automated verdict is issued.
""".strip(),
)

SAMPLE_REVIEW_PROCEDURES = Document(
    id="doc-sample-review",
    title="Incident Review Procedures",
    doc_type=DocType.REVIEW_PROCEDURES,
    institution="AI Exam Guardian Demo",
    content="""
# Incident Review Procedures

## When a Session is Flagged

A session is flagged for teacher review when the risk score exceeds the configured threshold.
The teacher will review:

1. The behavioral evidence timeline
2. Risk scores and contributing events
3. AI assistant detection signals
4. Retrieved policy context

## Student Rights

Students have the right to:
- Review the evidence collected about their session
- Provide context or explanation to the reviewing teacher
- Appeal any determination through the institution's standard appeal process

## Important Limitations

The system provides evidence for human review — not automated verdicts.
No determination of academic misconduct should be made based solely on automated signals.
The reviewing teacher must consider all available context before reaching a conclusion.
""".strip(),
)

SAMPLE_DETECTION_EXPLANATION = Document(
    id="doc-sample-detection",
    title="How Detection Works",
    doc_type=DocType.DETECTION_EXPLANATION,
    institution="AI Exam Guardian Demo",
    content="""
# How AI Exam Guardian Detection Works

## Observable Signals

The system collects the following signals during an active exam session:
- Window focus and blur events
- Tab switch events
- Copy and paste events (paste length only — text content is never captured)
- Fullscreen exit events
- Navigation to known AI assistant domains
- Keyboard shortcut signals

## Detection States

- DETECTED: Observable signals strongly associated with AI assistant use
- SUSPECTED: Behavioral patterns consistent with AI assistant use
- NOT_DETECTED: No observable signals detected
- UNOBSERVABLE: The activity cannot be observed by available browser APIs

## Important Limitations

No browser-based system can detect all AI assistant usage with certainty.
Some tools (notably ParakeetAI) are specifically designed to evade detection.
Absence of a DETECTED signal does not prove the software was not used.
The final determination always belongs to the teacher or institution.

## Evidence vs Inference

Every report clearly distinguishes:
- OBSERVED EVIDENCE: what was actually recorded by the browser extension
- POLICY INTERPRETATION: what the configured policy says
- AI INFERENCE: what the AI model is inferring from the evidence
""".strip(),
)

ALL_SAMPLE_DOCUMENTS = [
    SAMPLE_EXAM_POLICY,
    SAMPLE_AI_POLICY,
    SAMPLE_REVIEW_PROCEDURES,
    SAMPLE_DETECTION_EXPLANATION,
]
