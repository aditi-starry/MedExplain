"""
Medical knowledge base: curated passages, a BM25 retriever and a lightweight knowledge graph.

Retrieval is deliberately simple and dependency-free (pure-Python BM25 with
synonym expansion from the knowledge graph), so it runs on small free-tier hosts.
See knowledge/README.md for how to add or update sources.
"""
import json
import logging
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set

from app.config import KNOWLEDGE_DIR

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[./][a-z0-9]+)*|[\u0900-\u097f]+")
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "is", "are", "be", "can", "it", "this", "that",
    "my", "your", "you", "i", "me", "what", "why", "how", "does", "do", "for", "with", "on", "as",
    "by", "at", "from", "about", "mean", "means", "result", "results", "level", "levels", "test",
    "value", "values", "report", "please", "explain", "tell", "should", "would", "could", "am", "was",
}


def tokenize(text: str) -> List[str]:
    tokens = _TOKEN_RE.findall((text or "").lower())
    return [t for t in tokens if t not in _STOPWORDS and (len(t) > 1 or t.isdigit())]


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    publisher: str
    url: str
    last_updated: Optional[str]
    retrieved: Optional[str]
    license: str


@dataclass(frozen=True)
class Passage:
    id: str
    text: str
    topics: Sequence[str]
    parameters: Sequence[str]
    document: SourceDocument


@dataclass
class Evidence:
    passage: Passage
    score: float

    def to_dict(self) -> Dict:
        doc = self.passage.document
        return {
            "id": self.passage.id,
            "text": self.passage.text,
            "score": round(self.score, 3),
            "sourceId": doc.id,
            "title": doc.title,
            "publisher": doc.publisher,
            "url": doc.url,
            "lastUpdated": doc.last_updated,
            "retrieved": doc.retrieved,
        }


@dataclass
class Relationship:
    id: str
    members: List[str]
    type: str
    description: str
    evidence: List[str]


@dataclass
class KnowledgeBase:
    passages: Dict[str, Passage] = field(default_factory=dict)
    documents: Dict[str, SourceDocument] = field(default_factory=dict)
    aliases: Dict[str, List[str]] = field(default_factory=dict)       # canonical -> aliases
    panels: Dict[str, str] = field(default_factory=dict)              # canonical -> panel
    concepts: Dict[str, Dict] = field(default_factory=dict)           # concept id -> concept
    parameter_concepts: Dict[str, List[str]] = field(default_factory=dict)
    relationships: List[Relationship] = field(default_factory=list)
    # BM25 index
    _doc_tokens: Dict[str, List[str]] = field(default_factory=dict)
    _df: Dict[str, int] = field(default_factory=dict)
    _avgdl: float = 0.0

    # ---------- loading ----------
    @classmethod
    def load(cls, root: Path) -> "KnowledgeBase":
        kb = cls()
        for path in sorted((root / "documents").glob("*.json")):
            with open(path, "r", encoding="utf-8") as f:
                collection = json.load(f)
            for d in collection.get("documents", []):
                doc = SourceDocument(
                    id=d["id"],
                    title=d["title"],
                    publisher=d.get("publisher", collection.get("publisher", "")),
                    url=d["url"],
                    last_updated=d.get("lastUpdated"),
                    retrieved=d.get("retrieved", collection.get("retrieved")),
                    license=collection.get("license", ""),
                )
                kb.documents[doc.id] = doc
                for p in d.get("passages", []):
                    kb.passages[p["id"]] = Passage(
                        id=p["id"], text=p["text"], topics=tuple(p.get("topics", [])),
                        parameters=tuple(d.get("parameters", [])), document=doc,
                    )
        graph_path = root / "graph.json"
        if graph_path.exists():
            with open(graph_path, "r", encoding="utf-8") as f:
                graph = json.load(f)
            kb.concepts = {c["id"]: c for c in graph.get("concepts", [])}
            for node in graph.get("parameters", []):
                kb.aliases[node["id"]] = list(node.get("aliases", []))
                kb.panels[node["id"]] = node.get("panel", "Other")
                kb.parameter_concepts[node["id"]] = list(node.get("concepts", []))
            kb.relationships = [
                Relationship(r["id"], list(r["members"]), r["type"], r["description"], list(r["evidence"]))
                for r in graph.get("relationships", [])
            ]
        kb._build_index()
        return kb

    def _build_index(self) -> None:
        self._doc_tokens = {}
        self._df = {}
        for pid, p in self.passages.items():
            # Index passage text, its topics, the document title and the parameter names it covers
            extra = " ".join(list(p.topics) + [p.document.title] + list(p.parameters))
            toks = tokenize(p.text + " " + extra)
            self._doc_tokens[pid] = toks
            for t in set(toks):
                self._df[t] = self._df.get(t, 0) + 1
        n = len(self._doc_tokens) or 1
        self._avgdl = sum(len(v) for v in self._doc_tokens.values()) / n

    # ---------- validation ----------
    def validate(self) -> List[str]:
        """Returns a list of problems (empty when the knowledge base is consistent)."""
        problems = []
        for pid, p in self.passages.items():
            if not p.document.url.startswith("https://"):
                problems.append(f"{pid}: source URL must be https")
            if len(p.text) > 600:
                problems.append(f"{pid}: passage longer than 600 characters")
        for rel in self.relationships:
            if len(rel.members) < 2:
                problems.append(f"{rel.id}: relationship needs at least two members")
            for e in rel.evidence:
                if e not in self.passages:
                    problems.append(f"{rel.id}: unknown evidence passage {e}")
            for m in rel.members:
                if m not in self.aliases:
                    problems.append(f"{rel.id}: unknown parameter {m}")
        for cid, c in self.concepts.items():
            for e in c.get("evidence", []):
                if e not in self.passages:
                    problems.append(f"concept {cid}: unknown evidence passage {e}")
        return problems

    # ---------- graph helpers ----------
    def canonical_name(self, name: str) -> Optional[str]:
        """Maps a parameter name or alias (any case) to the graph's canonical name."""
        if not name:
            return None
        low = name.strip().lower()
        for canonical, aliases in self.aliases.items():
            if low == canonical.lower() or low in (a.lower() for a in aliases):
                return canonical
        return None

    def mentioned_parameters(self, text: str, candidates: Iterable[str]) -> List[str]:
        """Finds which of the candidate parameter names (or their aliases) appear in free text."""
        low = (text or "").lower()
        found = []
        for name in candidates:
            canonical = self.canonical_name(name) or name
            terms = [name, canonical] + self.aliases.get(canonical, [])
            for term in terms:
                term_low = term.lower()
                if not term_low:
                    continue
                if re.search(r"[\u0900-\u097f]", term_low):
                    hit = term_low in low
                else:
                    hit = re.search(r"(?<![a-z0-9])" + re.escape(term_low) + r"(?![a-z0-9])", low) is not None
                # Very short aliases (e.g. "k", "na") only count when written in upper case
                if hit and len(term_low) <= 2 and not re.search(r"(?<![A-Za-z])" + re.escape(term.upper()) + r"(?![A-Za-z])", text or ""):
                    hit = False
                if hit:
                    found.append(name)
                    break
        return found

    def relationships_for(self, names: Iterable[str]) -> List[Relationship]:
        canon = {self.canonical_name(n) or n for n in names}
        return [r for r in self.relationships if canon.intersection(r.members)]

    def passages_for_parameter(self, name: str) -> List[Passage]:
        canonical = self.canonical_name(name) or name
        return [p for p in self.passages.values() if canonical in p.parameters]

    # ---------- retrieval ----------
    def _bm25(self, query_tokens: List[str], pid: str, k1: float = 1.4, b: float = 0.75) -> float:
        toks = self._doc_tokens.get(pid, [])
        if not toks:
            return 0.0
        n = len(self._doc_tokens)
        dl = len(toks)
        score = 0.0
        for q in set(query_tokens):
            tf = toks.count(q)
            if not tf:
                continue
            df = self._df.get(q, 0)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / self._avgdl))
        return score

    def retrieve(
        self,
        query: str,
        parameters: Sequence[str] = (),
        topics: Sequence[str] = (),
        k: int = 4,
        min_score: float = 1.0,
    ) -> List[Evidence]:
        """
        Retrieves the passages most relevant to a query and/or parameter names.

        - Parameter names are expanded with their graph aliases.
        - Passages that explicitly cover a requested parameter get a boost.
        - Results below `min_score` are dropped, so an empty list means
          "no sufficiently relevant evidence" (missing-evidence detection).
        """
        canon_params = [self.canonical_name(p) or p for p in parameters]
        expanded = [query]
        for cp in canon_params:
            expanded.append(cp)
            expanded.extend(self.aliases.get(cp, []))
        expanded.extend(topics)
        q_tokens = tokenize(" ".join(expanded))
        if not q_tokens:
            return []
        wanted = set(canon_params)
        wanted_topics = set(topics)
        scored = []
        for pid, passage in self.passages.items():
            score = self._bm25(q_tokens, pid)
            if wanted:
                if wanted.intersection(passage.parameters):
                    score += 2.5
                elif passage.parameters:
                    score *= 0.35  # passage is about other tests
            if wanted_topics.intersection(passage.topics):
                score += 0.75
            # Prefer passages about the same direction as the result (high vs low)
            for wanted_dir, other_dir in (("high", "low"), ("low", "high")):
                if wanted_dir in wanted_topics and other_dir in passage.topics and wanted_dir not in passage.topics:
                    score *= 0.5
            if score >= min_score:
                scored.append(Evidence(passage, score))
        scored.sort(key=lambda e: e.score, reverse=True)
        return scored[:k]

    def evidence_for_parameter(self, name: str, evaluation: Optional[str], k: int = 3) -> List[Evidence]:
        """Evidence for explaining one result: definition + passages about its direction."""
        topics = ["definition", "interpretation"]
        if evaluation == "Above Range":
            topics.append("high")
        elif evaluation == "Below Range":
            topics.append("low")
        canonical = self.canonical_name(name)
        if canonical is None or not self.passages_for_parameter(canonical):
            return []  # nothing in the knowledge base is about this test
        return self.retrieve(" ".join([canonical] + topics), parameters=[canonical], topics=topics, k=k, min_score=2.0)


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    kb = KnowledgeBase.load(KNOWLEDGE_DIR)
    problems = kb.validate()
    if problems:
        logger.warning("Knowledge base validation issues: %s", "; ".join(problems[:10]))
    logger.info("Knowledge base loaded: %d passages from %d sources, %d relationships",
                len(kb.passages), len(kb.documents), len(kb.relationships))
    return kb


def resolve_sources(passage_ids: Iterable[str]) -> List[Dict]:
    """Turns passage ids into de-duplicated citation objects (only ids that really exist)."""
    kb = get_knowledge_base()
    out, seen = [], set()
    for pid in passage_ids:
        p = kb.passages.get(pid)
        if not p or pid in seen:
            continue
        seen.add(pid)
        out.append(Evidence(p, 0.0).to_dict())
    return out


def numbers_in(texts: Iterable[str]) -> Set[float]:
    found: Set[float] = set()
    for t in texts:
        for m in re.findall(r"\d+(?:\.\d+)?", t or ""):
            try:
                found.add(round(float(m), 4))
            except ValueError:
                pass
    return found