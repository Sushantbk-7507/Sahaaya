"""Data analytics and similarity recommendations using Pandas, NumPy, and Scikit-learn."""

from collections import Counter
import math
import re
import sqlite3
from typing import Any, Dict, List

import numpy as np
import pandas as pd

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    SKLEARN_AVAILABLE = True
except (ImportError, OSError):
    SKLEARN_AVAILABLE = False

_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "to", "with",
}


def _numpy_tfidf_cosine_similarities(corpus: List[str], target_idx: int) -> np.ndarray:
    """Pure-NumPy TF-IDF cosine similarity fallback when sklearn DLLs are blocked."""
    tokenized = [
        [t for t in re.findall(r"[a-z0-9]+", doc.lower()) if t not in _STOP_WORDS]
        for doc in corpus
    ]
    vocab = sorted({tok for tokens in tokenized for tok in tokens})
    if not vocab:
        return np.zeros(len(corpus), dtype=float)

    word_to_idx = {w: i for i, w in enumerate(vocab)}
    n_docs = len(corpus)
    df = np.zeros(len(vocab), dtype=float)
    tf_matrix = np.zeros((n_docs, len(vocab)), dtype=float)

    for doc_i, tokens in enumerate(tokenized):
        counts = Counter(tokens)
        for tok, cnt in counts.items():
            col = word_to_idx[tok]
            tf_matrix[doc_i, col] = float(cnt)
            df[col] += 1.0

    idf = np.log((1.0 + n_docs) / (1.0 + df)) + 1.0
    tfidf = tf_matrix * idf
    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = tfidf / norms
    return (normalized @ normalized[target_idx]).flatten()


def compute_admin_analytics(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Compute real-time platform analytics from SQLite tables using Pandas and NumPy."""
    org_rows = conn.execute(
        """
        SELECT id, organization_name, category, area, city, verification_status
        FROM organizations
        """
    ).fetchall()
    req_rows = conn.execute(
        """
        SELECT id, organization_id, requirement_category, priority
        FROM assistance_requirements
        """
    ).fetchall()
    report_rows = conn.execute(
        """
        SELECT id, reason, status
        FROM reports
        """
    ).fetchall()

    org_df = pd.DataFrame([dict(r) for r in org_rows])
    req_df = pd.DataFrame([dict(r) for r in req_rows])
    report_df = pd.DataFrame([dict(r) for r in report_rows])

    if org_df.empty:
        return {
            "category_counts": {},
            "status_counts": {},
            "top_areas": {},
            "requirement_category_counts": {},
            "requirement_priority_counts": {},
            "report_status_counts": {},
            "avg_reqs_per_verified_org": 0.0,
            "high_priority_req_count": 0,
        }

    category_counts = org_df["category"].value_counts().to_dict()
    status_counts = org_df["verification_status"].value_counts().to_dict()
    top_areas = org_df["area"].value_counts().head(6).to_dict()

    if req_df.empty:
        req_cat_counts: Dict[str, int] = {}
        req_prio_counts: Dict[str, int] = {}
        high_prio_count = 0
        avg_reqs = 0.0
    else:
        req_cat_counts = req_df["requirement_category"].value_counts().to_dict()
        req_prio_counts = req_df["priority"].value_counts().to_dict()
        high_prio_count = int((req_df["priority"] == "High").sum())

        approved_ids = set(
            org_df.loc[org_df["verification_status"] == "Approved", "id"].tolist()
        )
        if approved_ids:
            counts_per_org = [
                int((req_df["organization_id"] == oid).sum()) for oid in approved_ids
            ]
            avg_reqs = round(float(np.mean(counts_per_org)), 2)
        else:
            avg_reqs = 0.0

    report_status_counts = (
        report_df["status"].value_counts().to_dict() if not report_df.empty else {}
    )

    return {
        "category_counts": {str(k): int(v) for k, v in category_counts.items()},
        "status_counts": {str(k): int(v) for k, v in status_counts.items()},
        "top_areas": {str(k): int(v) for k, v in top_areas.items()},
        "requirement_category_counts": {str(k): int(v) for k, v in req_cat_counts.items()},
        "requirement_priority_counts": {str(k): int(v) for k, v in req_prio_counts.items()},
        "report_status_counts": {str(k): int(v) for k, v in report_status_counts.items()},
        "avg_reqs_per_verified_org": avg_reqs,
        "high_priority_req_count": high_prio_count,
    }


def find_similar_organizations(
    conn: sqlite3.Connection,
    org_id: int,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """Recommend similar verified organizations using TF-IDF and cosine similarity."""
    orgs = conn.execute(
        """
        SELECT id, organization_name, category, description, area, city,
               facilities, image_filename
        FROM organizations
        WHERE verification_status = 'Approved'
        ORDER BY id ASC
        """
    ).fetchall()

    if len(orgs) < 2:
        return []

    req_rows = conn.execute(
        """
        SELECT organization_id, requirement_category, item_name
        FROM assistance_requirements
        """
    ).fetchall()

    req_by_org: Dict[int, List[str]] = {}
    for row in req_rows:
        oid = row["organization_id"]
        req_by_org.setdefault(oid, []).append(
            f"{row['requirement_category']} {row['item_name']}"
        )

    records = [dict(o) for o in orgs]
    target_idx = next((i for i, r in enumerate(records) if r["id"] == org_id), None)
    if target_idx is None:
        return []

    corpus = []
    for rec in records:
        req_text = " ".join(req_by_org.get(rec["id"], []))
        doc = (
            f"{rec['category']} {rec['category']} {rec['area']} {rec['city']} "
            f"{rec['facilities']} {rec['description']} {req_text}"
        )
        corpus.append(doc)

    if SKLEARN_AVAILABLE:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(corpus)
        similarities = cosine_similarity(
            tfidf_matrix[target_idx:target_idx + 1], tfidf_matrix
        ).flatten()
    else:
        similarities = _numpy_tfidf_cosine_similarities(corpus, target_idx)

    ranked_indices = np.argsort(similarities)[::-1]
    results: List[Dict[str, Any]] = []
    for idx in ranked_indices:
        if idx == target_idx:
            continue
        score = float(similarities[idx])
        item = dict(records[idx])
        item["similarity_pct"] = max(1, min(99, int(round(score * 100))))
        results.append(item)
        if len(results) >= top_k:
            break

    return results
