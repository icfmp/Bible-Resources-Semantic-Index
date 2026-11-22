#!/usr/bin/env python3
"""Read-only audit: old ACAI-facing descriptors after BSI identity corrections.

No field is silently edited. It identifies records whose current classification
or canonical identity differs from their historical source and whose inherited
claims therefore need independent editorial review before public presentation.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUMAN_RELATIONS = {"father", "mother", "siblings", "spouse", "wives", "husbands",
                   "children", "sons", "daughters", "parents", "gender", "birth_place",
                   "birth_date", "death_date", "related_people"}
SOURCE_PREFIXES = {
    "people": "person", "places": "place", "groups": "group",
    "deities": "deity", "fauna": "fauna", "flora": "flora",
    "realia": "realia", "keyterms": "keyterm",
}


def audit(data: Path) -> dict:
    # Review only explicit BSI identity corrections, not every inherited ACAI
    # primary_id alias. A historical alias is not automatically an anomaly.
    decisions_file = data / "editorial-decisions.json"
    decisions = json.loads(decisions_file.read_text(encoding="utf-8"))["decisions"]
    explicit_replacements = {row["source_id"] for row in decisions
                             if row["action"] == "replace_identity" and not row["source_id"].startswith("keyterm:")}
    audited = []
    source_ids = set()
    for directory in sorted((data / "entities").iterdir()):
        if not directory.is_dir():
            continue
        original_prefix = SOURCE_PREFIXES.get(directory.name)
        if original_prefix is None:
            raise ValueError(f"Unknown native entity source category: {directory}")
        for path in sorted(directory.glob("*.json")):
            record = json.loads(path.read_text(encoding="utf-8"))
            meta = record["bsi"]
            source_id = meta["source_id"]
            if source_id in source_ids:
                raise ValueError(f"Duplicate source identity: {source_id}")
            source_ids.add(source_id)
            if not source_id.startswith(original_prefix + ":"):
                raise ValueError(f"Source category mismatch: {path}")
            if source_id not in explicit_replacements:
                continue
            original_type = original_prefix
            current_type = record["type"]
            current_id = record["id"]
            reclassified = current_type != original_type
            identity_changed = current_id != source_id
            canonical_id = meta.get("canonical_id")
            if not (reclassified or identity_changed or (canonical_id and canonical_id != source_id)):
                continue
            issues = []
            if reclassified:
                issues.append("type_reclassified")
            if identity_changed:
                issues.append("id_reclassified")
            if canonical_id and canonical_id != source_id:
                issues.append("canonical_identity_changed")
            human = sorted(HUMAN_RELATIONS.intersection(record))
            if reclassified and current_type != "person" and human:
                issues.append("inherited_person_specific_fields")
            aliases = record.get("referred_to_as")
            if aliases:
                issues.append("inherited_identity_aliases_need_review")
            localized = record.get("localizations", {})
            original_articles = []
            labels = {}
            for language, obj in sorted(localized.items()):
                descriptions = obj.get("descriptions", []) if isinstance(obj, dict) else []
                for i, row in enumerate(descriptions):
                    if isinstance(row, dict) and row.get("source") == "acai":
                        original_articles.append({"lang": language, "index": i,
                                                  "article": row.get("article"),
                                                  "description": row.get("description")})
                if isinstance(obj, dict) and obj.get("preferred_label"):
                    labels[language] = obj["preferred_label"]
            if (reclassified or identity_changed or canonical_id != source_id) and original_articles:
                issues.append("inherited_unreviewed_descriptions")
            audited.append({
                "path": path.relative_to(data).as_posix(),
                "source_id": source_id,
                "current_id": current_id,
                "current_type": current_type,
                "canonical_id": canonical_id,
                "review_reason": meta.get("editorial_reason"),
                "issue_codes": sorted(set(issues)),
                "person_specific_fields": human,
                "inherited_aliases": aliases,
                "source_descriptions": original_articles,
                "source_labels": labels,
            })
    if {item["source_id"] for item in audited} != explicit_replacements:
        raise ValueError("Some reviewed BSI identity changes were not found in native entity data")
    counter = Counter(code for record in audited for code in record["issue_codes"])
    return {"schema_version": 1, "policy": "read_only_preserve_original_editorial_text",
            "reviewed_changed_identity_records": len(audited),
            "issue_counts": dict(sorted(counter.items())),
            "items": audited}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=ROOT / "data")
    p.add_argument("--report", type=Path)
    a = p.parse_args()
    result = audit(a.data)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
    print(json.dumps({"reviewed_changed_identity_records": result["reviewed_changed_identity_records"],
                      "issue_counts": result["issue_counts"],
                      "summary": [{"source_id": x["source_id"], "current_id": x["current_id"],
                                   "issue_codes": x["issue_codes"],
                                   "person_specific_fields": x["person_specific_fields"]}
                                  for x in result["items"]]}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
