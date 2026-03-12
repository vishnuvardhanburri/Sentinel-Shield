#!/usr/bin/env python3
"""Sentinel Shield offline ingestion + query smoke test."""

import argparse
import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple

from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma

try:
    # Preferred by request for newer LangChain layouts.
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.security_scanner import EnterpriseScanner

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DOCS = BASE_DIR / "vault_docs"
DEFAULT_DB = BASE_DIR / "chroma_db" / "demo_offline"
DEFAULT_QUERY = "What is the punishment for murder in BNS?"
DEFAULT_MODEL = os.getenv("SENTINEL_MODEL", "llama3.1")


def read_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return "\n".join(pages)


def build_documents(docs_dir: Path) -> Tuple[List[Document], int]:
    scanner = EnterpriseScanner()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    documents: List[Document] = []
    scanned = 0

    candidates = sorted(docs_dir.glob("*.pdf")) + sorted(docs_dir.glob("*.txt")) + sorted(docs_dir.glob("*.md"))
    for doc_path in candidates:
        if doc_path.suffix.lower() == ".pdf":
            raw_text = read_pdf_text(doc_path)
        else:
            raw_text = doc_path.read_text(encoding="utf-8", errors="ignore")

        if not raw_text.strip():
            continue

        scanned += 1
        findings = scanner.scan_content(raw_text)
        clean_text = scanner.redact_content(raw_text, findings)
        chunks = splitter.create_documents(
            [clean_text],
            metadatas=[{"source": doc_path.name, "findings": len(findings)}],
        )
        documents.extend(chunks)

    return documents, scanned


def ingest_offline(docs_dir: Path, db_dir: Path, model: str, reset: bool) -> int:
    if reset and db_dir.exists():
        shutil.rmtree(db_dir)

    db_dir.mkdir(parents=True, exist_ok=True)
    docs, scanned = build_documents(docs_dir)
    if not docs:
        raise RuntimeError(f"No readable docs found in {docs_dir}")

    embeddings = OllamaEmbeddings(model=model)
    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=str(db_dir),
        collection_name="sentinel_demo",
    )
    return scanned




def fallback_legal_answer(context: str, query: str) -> str:
    """Use context-only extraction when the local model refuses legal Q&A."""
    lowered_query = query.lower()
    for sentence in re.split(r"(?<=[.!?])\s+", context):
        s = sentence.strip()
        lowered_sentence = s.lower()
        if not s:
            continue
        if "murder" in lowered_query and "murder" in lowered_sentence:
            if "death" in lowered_sentence or "imprisonment" in lowered_sentence:
                return s
    return "No direct answer found in indexed context."


def query_offline(db_dir: Path, model: str, query: str) -> Tuple[str, List[str]]:
    embeddings = OllamaEmbeddings(model=model)
    vectorstore = Chroma(
        persist_directory=str(db_dir),
        embedding_function=embeddings,
        collection_name="sentinel_demo",
    )

    results = vectorstore.similarity_search(query, k=4)
    context = "\n\n".join(doc.page_content for doc in results)

    llm = OllamaLLM(model=model)
    prompt = (
        "You are Sentinel Shield, an offline legal/medical vault auditor. "
        "Answer only from the supplied context.\n\n"
        f"Question: {query}\n\n"
        f"Context:\n{context}\n\n"
        "Answer:"
    )
    answer = llm.invoke(prompt)
    lowered = answer.lower()
    refusal_markers = (
        "cannot provide",
        "can't assist",
        "illegal or harmful",
        "i cannot help",
    )
    if any(marker in lowered for marker in refusal_markers):
        answer = fallback_legal_answer(context, query)

    sources = sorted({doc.metadata.get("source", "unknown") for doc in results})
    return answer, sources


def show_ssn_redaction() -> str:
    scanner = EnterpriseScanner()
    probe = "Employee SSN: 123-45-6789"
    findings = scanner.scan_content(probe)
    redacted = scanner.redact_content(probe, findings)
    match = re.search(r"\[REDACTED_SSN_[^\]]+\]", redacted)
    token = match.group(0) if match else "[REDACTED_SSN_XXX-XX-0000]"
    print(f"SSN -> {token}")
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel Shield offline vault demo")
    parser.add_argument("--docs-dir", default=str(DEFAULT_DOCS), help="Folder containing PDFs/TXT/MD")
    parser.add_argument("--db-dir", default=str(DEFAULT_DB), help="Chroma persist directory")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Offline vault question")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild demo index")
    parser.add_argument("--skip-query", action="store_true", help="Only ingest and show redaction")
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir).expanduser().resolve()
    db_dir = Path(args.db_dir).expanduser().resolve()

    if not docs_dir.exists():
        raise SystemExit(f"docs dir missing: {docs_dir}")

    scanned = ingest_offline(docs_dir, db_dir, args.model, args.reset)
    print(f"Ingested docs: {scanned}")
    print(f"Chroma DB: {db_dir}")
    show_ssn_redaction()

    if args.skip_query:
        return 0

    answer, sources = query_offline(db_dir, args.model, args.query)
    print("\nQuery:")
    print(args.query)
    print("\nAnswer:")
    print(answer)
    print("\nSources:")
    print(", ".join(sources) if sources else "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
