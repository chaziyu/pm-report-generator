"""
Metrics calculations for PM Report evaluation.
Computes classification accuracy, confusion matrices, calibration buckets,
extraction accuracy per field, rule validation, OCR anchor detection, and timing performance.
"""

from typing import Dict, List, Any, Optional
import statistics

CALIBRATION_BUCKETS = [
    ("0.00-0.49", 0.0, 0.50),
    ("0.50-0.69", 0.50, 0.70),
    ("0.70-0.79", 0.70, 0.80),
    ("0.80-0.89", 0.80, 0.90),
    ("0.90-0.94", 0.90, 0.95),
    ("0.95-1.00", 0.95, 1.01),
]

def compute_classification_metrics(records: List[Dict[str, Any]], categories: List[str]) -> Dict[str, Any]:
    """
    Computes classification summary metrics from image-level evaluation records.
    """
    total = len(records)
    if total == 0:
        return {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "unknown": 0,
            "accuracy": 0.0,
            "high_confidence_wrong_count": 0,
            "medium_confidence_wrong_count": 0,
            "unknown_rate": 0.0,
            "per_category": {},
            "confusion_matrix": {},
            "calibration_buckets": {},
            "high_confidence_wrong_samples": [],
            "medium_confidence_wrong_samples": [],
        }

    correct_count = sum(1 for r in records if r["correct"])
    unknown_count = sum(1 for r in records if r["predicted_category"] == "unknown")
    incorrect_count = total - correct_count

    # Per-category metrics
    per_cat: Dict[str, Dict[str, Any]] = {}
    for cat in categories:
        cat_records = [r for r in records if r["expected_category"] == cat]
        c_tot = len(cat_records)
        c_corr = sum(1 for r in cat_records if r["correct"])
        c_multi_corr = sum(1 for r in cat_records if r.get("in_assigned_categories", False))
        c_unk = sum(1 for r in cat_records if r["predicted_category"] == "unknown")
        c_inc = c_tot - c_corr
        per_cat[cat] = {
            "total": c_tot,
            "correct": c_corr,
            "incorrect": c_inc,
            "unknown": c_unk,
            "accuracy": round(c_corr / c_tot, 4) if c_tot > 0 else 0.0,
            "multi_label_correct": c_multi_corr,
            "multi_label_accuracy": round(c_multi_corr / c_tot, 4) if c_tot > 0 else 0.0,
        }

    # Confusion matrix: expected -> predicted -> count
    all_col_cats = sorted(list(set(categories + ["unknown"] + [r["predicted_category"] for r in records])))
    confusion: Dict[str, Dict[str, int]] = {cat: {col: 0 for col in all_col_cats} for cat in categories}
    for r in records:
        exp = r["expected_category"]
        pred = r["predicted_category"]
        if exp in confusion:
            confusion[exp][pred] = confusion[exp].get(pred, 0) + 1

    # High / Medium confidence errors
    high_conf_wrong = [r for r in records if not r["correct"] and r["confidence"] >= 0.90]
    med_conf_wrong = [r for r in records if not r["correct"] and 0.70 <= r["confidence"] < 0.90]

    # Calibration buckets
    buckets: Dict[str, Dict[str, Any]] = {}
    for name, low, high in CALIBRATION_BUCKETS:
        b_records = [r for r in records if low <= r["confidence"] < high]
        b_tot = len(b_records)
        b_corr = sum(1 for r in b_records if r["correct"])
        buckets[name] = {
            "total": b_tot,
            "correct": b_corr,
            "accuracy": round(b_corr / b_tot, 4) if b_tot > 0 else 0.0,
        }

    # Slot conformance & multi-label metrics
    multi_label_correct = sum(1 for r in records if r.get("in_assigned_categories", False))
    canonical_slot_count = sum(1 for r in records if r.get("is_source_slot_canonical", True))
    noncanonical_slot_count = total - canonical_slot_count

    return {
        "total": total,
        "correct": correct_count,
        "incorrect": incorrect_count,
        "unknown": unknown_count,
        "accuracy": round(correct_count / total, 4),
        "multi_label_correct": multi_label_correct,
        "multi_label_accuracy": round(multi_label_correct / total, 4),
        "slot_conformance": {
            "canonical_slot_count": canonical_slot_count,
            "noncanonical_slot_count": noncanonical_slot_count,
            "canonical_slot_match_rate": round(canonical_slot_count / total, 4),
        },
        "high_confidence_wrong_count": len(high_conf_wrong),
        "medium_confidence_wrong_count": len(med_conf_wrong),
        "unknown_rate": round(unknown_count / total, 4),
        "per_category": per_cat,
        "confusion_matrix": confusion,
        "calibration_buckets": buckets,
        "high_confidence_wrong_samples": [
            {
                "case_id": r["case_id"],
                "appendix_number": r.get("source_appendix_number", r.get("appendix_number")),
                "image_filename": r["image_filename"],
                "expected": r["expected_category"],
                "predicted": r["predicted_category"],
                "confidence": r["confidence"],
            }
            for r in high_conf_wrong
        ],
        "medium_confidence_wrong_samples": [
            {
                "case_id": r["case_id"],
                "appendix_number": r.get("source_appendix_number", r.get("appendix_number")),
                "image_filename": r["image_filename"],
                "expected": r["expected_category"],
                "predicted": r["predicted_category"],
                "confidence": r["confidence"],
            }
            for r in med_conf_wrong
        ],
    }

def compute_extraction_metrics(case_results: List[Dict[str, Any]], field_names: List[str]) -> Dict[str, Any]:
    """
    Computes extraction metrics across evaluated cases.
    """
    field_summary: Dict[str, Dict[str, Any]] = {}

    for field in field_names:
        tested = 0
        correct = 0
        incorrect = 0
        missing = 0
        root_causes: Dict[str, int] = {}

        for cr in case_results:
            field_data = cr.get("fields", {}).get(field)
            if field_data is None or field_data.get("expected") is None:
                continue

            tested += 1
            if field_data.get("correct"):
                correct += 1
            else:
                incorrect += 1
                if field_data.get("extracted") is None:
                    missing += 1
                rc = field_data.get("root_cause", "UNKNOWN")
                root_causes[rc] = root_causes.get(rc, 0) + 1

        field_summary[field] = {
            "tested": tested,
            "correct": correct,
            "incorrect": incorrect,
            "missing": missing,
            "accuracy": round(correct / tested, 4) if tested > 0 else 0.0,
            "root_causes": root_causes,
        }

    total_tested = sum(s["tested"] for s in field_summary.values())
    total_correct = sum(s["correct"] for s in field_summary.values())
    overall_acc = round(total_correct / total_tested, 4) if total_tested > 0 else 0.0

    return {
        "overall_accuracy": overall_acc,
        "total_fields_tested": total_tested,
        "total_fields_correct": total_correct,
        "fields": field_summary,
    }

def compute_rule_metrics(case_results: List[Dict[str, Any]], rule_names: List[str]) -> Dict[str, Any]:
    """
    Computes rule engine validation metrics across evaluated cases.
    """
    rule_summary: Dict[str, Dict[str, Any]] = {}
    for rule in rule_names:
        tested = 0
        correct = 0
        incorrect = 0
        for cr in case_results:
            rule_data = cr.get("rules", {}).get(rule)
            if rule_data is None or rule_data.get("expected") is None:
                continue
            tested += 1
            if rule_data.get("correct"):
                correct += 1
            else:
                incorrect += 1
        rule_summary[rule] = {
            "tested": tested,
            "correct": correct,
            "incorrect": incorrect,
            "accuracy": round(correct / tested, 4) if tested > 0 else 0.0,
        }
    return rule_summary

def compute_performance_metrics(durations: List[Dict[str, float]]) -> Dict[str, Any]:
    """
    Computes timing summary: average, median, min, max, total.
    """
    if not durations:
        return {
            "total_images": 0,
            "total_duration_ms": 0.0,
            "avg_image_duration_ms": 0.0,
            "median_image_duration_ms": 0.0,
            "min_image_duration_ms": 0.0,
            "max_image_duration_ms": 0.0,
            "slowest_image": None,
        }

    total_times = [d["total_ms"] for d in durations]
    total_sum = sum(total_times)
    avg_time = total_sum / len(total_times)
    med_time = statistics.median(total_times)
    min_time = min(total_times)
    max_time = max(total_times)

    slowest = max(durations, key=lambda d: d["total_ms"])

    return {
        "total_images": len(durations),
        "total_duration_ms": round(total_sum, 2),
        "avg_image_duration_ms": round(avg_time, 2),
        "median_image_duration_ms": round(med_time, 2),
        "min_image_duration_ms": round(min_time, 2),
        "max_image_duration_ms": round(max_time, 2),
        "slowest_image": slowest,
    }

def compute_ai_metrics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes local AI fallback metrics from image evaluation records.
    """
    total = len(records)
    if total == 0:
        return {
            "ai_invocations": 0,
            "ai_invocation_rate": 0.0,
            "ai_agreements": 0,
            "ai_agreement_rate": 0.0,
            "ai_disagreements": 0,
            "ai_disagreement_rate": 0.0,
            "multi_category_count": 0,
            "multi_category_evidence_accuracy": 0.0,
            "manual_review_count": 0,
            "manual_review_rate": 0.0,
            "latency": {
                "avg_ms": 0.0,
                "median_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "total_ms": 0.0,
            },
        }

    invoked_records = [r for r in records if r.get("ai_invoked", False)]
    invocations = len(invoked_records)

    agreements = sum(
        1 for r in invoked_records
        if r.get("arbitration_state") in ["AI_VERIFIED", "DETERMINISTIC_ACCEPTED"]
        or (r.get("predicted_category") == r.get("expected_category"))
    )
    disagreements = sum(
        1 for r in invoked_records
        if r.get("arbitration_state") == "DISAGREEMENT"
    )

    multi_cat_records = [
        r for r in records
        if r.get("is_ambiguous", False) or len(r.get("multi_category_evidenced", [])) > 1
    ]
    multi_cat_correct = sum(
        1 for r in multi_cat_records
        if r.get("expected_category") in r.get("multi_category_evidenced", [])
        or r.get("predicted_category") == r.get("expected_category")
    )
    multi_cat_acc = (
        round(multi_cat_correct / len(multi_cat_records), 4)
        if multi_cat_records else 1.0
    )

    review_count = sum(
        1 for r in records
        if r.get("arbitration_state") in ["REVIEW_REQUIRED", "DISAGREEMENT"]
        or r.get("review_status") in ["REVIEW_REQUIRED", "FLAGGED"]
        or not r.get("correct", False)
    )

    ai_latencies = [r.get("ai_latency_ms", 0.0) for r in invoked_records if r.get("ai_latency_ms", 0.0) > 0]
    if ai_latencies:
        lat_avg = round(sum(ai_latencies) / len(ai_latencies), 2)
        lat_med = round(statistics.median(ai_latencies), 2)
        lat_min = round(min(ai_latencies), 2)
        lat_max = round(max(ai_latencies), 2)
        lat_tot = round(sum(ai_latencies), 2)
    else:
        lat_avg = lat_med = lat_min = lat_max = lat_tot = 0.0

    return {
        "ai_invocations": invocations,
        "ai_invocation_rate": round(invocations / total, 4) if total > 0 else 0.0,
        "ai_agreements": agreements,
        "ai_agreement_rate": round(agreements / invocations, 4) if invocations > 0 else 0.0,
        "ai_disagreements": disagreements,
        "ai_disagreement_rate": round(disagreements / invocations, 4) if invocations > 0 else 0.0,
        "multi_category_count": len(multi_cat_records),
        "multi_category_evidence_accuracy": multi_cat_acc,
        "manual_review_count": review_count,
        "manual_review_rate": round(review_count / total, 4) if total > 0 else 0.0,
        "latency": {
            "avg_ms": lat_avg,
            "median_ms": lat_med,
            "min_ms": lat_min,
            "max_ms": lat_max,
            "total_ms": lat_tot,
        },
    }
