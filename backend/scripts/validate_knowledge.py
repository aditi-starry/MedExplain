"""
Validates the knowledge base (documents + graph) and prints a short summary.

Usage (from backend/):  python scripts/validate_knowledge.py
Exit code 1 when problems are found, so it can run in CI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import KNOWLEDGE_DIR  # noqa: E402
from app.services.knowledge_base import KnowledgeBase  # noqa: E402


def main() -> int:
    kb = KnowledgeBase.load(KNOWLEDGE_DIR)
    problems = kb.validate()
    covered = {p for passage in kb.passages.values() for p in passage.parameters}
    uncovered = sorted(set(kb.aliases) - covered)
    print(f"Sources: {len(kb.documents)}  Passages: {len(kb.passages)}  Relationships: {len(kb.relationships)}")
    print(f"Graph parameters without any passage (explanations will report missing evidence): {', '.join(uncovered) or 'none'}")
    for problem in problems:
        print("PROBLEM:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
