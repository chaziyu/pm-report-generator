"""
Report Generator for PM Report Dataset Evaluation.
Produces human-readable markdown reports adhering to Section 17 guidelines.
Ensures customer-sensitive strings and raw screenshots are not exposed.
"""

from typing import Dict, Any, List

def generate_markdown_report(
    summary: Dict[str, Any],
    classifier_results: Dict[str, Any],
    extraction_results: Dict[str, Any],
    ocr_results: Dict[str, Any],
    pipeline_results: Dict[str, Any],
    mode: str = "baseline"
) -> str:
    """
    Renders a comprehensive, human-readable markdown evaluation report.
    """
    c_metrics = classifier_results.get("metrics", {})
    e_metrics = extraction_results.get("fields", {})
    r_metrics = extraction_results.get("rules", {})
    perf = summary.get("performance", {})
    dataset_info = summary.get("dataset", {})

    lines: List[str] = []

    # Title
    if mode == "baseline":
        mode_title = "Baseline Evaluation Report"
    elif mode == "deterministic":
        mode_title = "Deterministic Pipeline Evaluation Report"
    elif mode == "deterministic_plus_ai":
        mode_title = "Deterministic + Local AI Fallback Evaluation Report"
    else:
        mode_title = "Post-Hardening Evaluation Report"

    lines.append(f"# FortiGate PM Report Generator: {mode_title}")
    lines.append("")
    lines.append("> **Offline Dataset-Driven Pipeline Evaluation & Hardening Report**")
    lines.append("")

    # 1. Dataset Summary
    lines.append("## 1. Dataset Summary")
    lines.append(f"- **Evaluated Cases**: {dataset_info.get('cases', 0)}")
    lines.append(f"- **Total Appendix Screenshots**: {dataset_info.get('images', 0)}")
    lines.append(f"- **Template Variant**: `fortigate_pm_v1`")
    lines.append(f"- **Evaluation Mode**: `{mode}`")
    lines.append(f"- **Total Duration**: {perf.get('total_duration_ms', 0)} ms (~{round(perf.get('total_duration_ms', 0)/1000, 2)} s)")
    lines.append(f"- **Avg Duration per Image**: {perf.get('avg_image_duration_ms', 0)} ms")
    lines.append(f"- **Median Duration per Image**: {perf.get('median_image_duration_ms', 0)} ms")
    slowest = perf.get("slowest_image")
    if slowest:
        lines.append(f"- **Slowest Image**: `{slowest.get('image')}` ({slowest.get('total_ms')} ms)")
    lines.append("")

    # AI Section if present
    ai_metrics = summary.get("ai")
    if ai_metrics and (mode == "deterministic_plus_ai" or ai_metrics.get("ai_invocations", 0) > 0):
        lines.append("## 1.1 Local AI Fallback & Interpretation (Qwen3-1.7B)")
        lines.append(f"- **AI Invocations**: {ai_metrics.get('ai_invocations', 0)} / {dataset_info.get('images', 0)} ({round(ai_metrics.get('ai_invocation_rate', 0.0) * 100, 2)}%)")
        lines.append(f"- **AI Agreement Rate**: {round(ai_metrics.get('ai_agreement_rate', 0.0) * 100, 2)}% ({ai_metrics.get('ai_agreements', 0)} agreements)")
        lines.append(f"- **AI Disagreement Rate**: {round(ai_metrics.get('ai_disagreement_rate', 0.0) * 100, 2)}% ({ai_metrics.get('ai_disagreements', 0)} disagreements)")
        lines.append(f"- **Multi-Category Screenshots Detected**: {ai_metrics.get('multi_category_count', 0)}")
        lines.append(f"- **Multi-Category Evidence Accuracy**: {round(ai_metrics.get('multi_category_evidence_accuracy', 0.0) * 100, 2)}%")
        lines.append(f"- **Manual Review Rate**: {round(ai_metrics.get('manual_review_rate', 0.0) * 100, 2)}% ({ai_metrics.get('manual_review_count', 0)} items)")
        ai_lat = ai_metrics.get("latency", {})
        lines.append(f"- **AI Processing Latency**: Avg: {ai_lat.get('avg_ms', 0)} ms | Median: {ai_lat.get('median_ms', 0)} ms | Max: {ai_lat.get('max_ms', 0)} ms")
        lines.append("")
        lines.append("> [!WARNING]")
        lines.append("> **Development Dataset Warning**: The current two-report dataset has been used for development and regression testing.")
        lines.append("> These results demonstrate fallback mechanics and multi-category arbitration, but must NOT be presented as unbiased proof that Qwen improves production accuracy.")
        lines.append("> AI accuracy claims require unseen holdout PM reports later.")
        lines.append("")
    lines.append("")

    # 2. Classification Accuracy
    lines.append("## 2. Classification Accuracy")
    lines.append(f"- **Overall Accuracy**: **{round(c_metrics.get('accuracy', 0.0) * 100, 2)}%** ({c_metrics.get('correct', 0)}/{c_metrics.get('total', 0)})")
    lines.append(f"- **High-Confidence Wrong (>= 0.90)**: {c_metrics.get('high_confidence_wrong_count', 0)}")
    lines.append(f"- **Medium-Confidence Wrong (0.70 - 0.89)**: {c_metrics.get('medium_confidence_wrong_count', 0)}")
    lines.append(f"- **Unknown Rate**: {round(c_metrics.get('unknown_rate', 0.0) * 100, 2)}% ({c_metrics.get('unknown', 0)} images)")
    lines.append("")

    # Confidence calibration
    lines.append("### Confidence Calibration")
    lines.append("| Confidence Bucket | Total Examples | Correct | Accuracy | Safe for Auto-Accept? |")
    lines.append("|---|---|---|---|---|")
    cal = c_metrics.get("calibration_buckets", {})
    for bucket_name, bdata in cal.items():
        acc = round(bdata.get("accuracy", 0.0) * 100, 1)
        tot = bdata.get("total", 0)
        corr = bdata.get("correct", 0)
        safe = "Yes" if acc == 100.0 and tot > 0 else ("Caution (<100%)" if tot > 0 else "N/A (No samples)")
        lines.append(f"| {bucket_name} | {tot} | {corr} | {acc}% | {safe} |")
    lines.append("")

    # 3. Per-Appendix Accuracy
    lines.append("## 3. Per-Appendix / Per-Category Accuracy")
    lines.append("| Appendix # | Category | Total | Correct | Incorrect | Unknown | Accuracy |")
    lines.append("|---|---|---|---|---|---|---|")
    per_cat = c_metrics.get("per_category", {})
    from .classifier_evaluator import APPENDIX_TO_CATEGORY
    for app_num in sorted(APPENDIX_TO_CATEGORY.keys()):
        cat = APPENDIX_TO_CATEGORY[app_num]
        cdata = per_cat.get(cat, {})
        tot = cdata.get("total", 0)
        corr = cdata.get("correct", 0)
        inc = cdata.get("incorrect", 0)
        unk = cdata.get("unknown", 0)
        acc = round(cdata.get("accuracy", 0.0) * 100, 1) if tot > 0 else 0.0
        lines.append(f"| App {app_num:02d} | `{cat}` | {tot} | {corr} | {inc} | {unk} | {acc}% |")
    lines.append("")

    # 4. Confusion Matrix
    lines.append("## 4. Confusion Matrix")
    conf = c_metrics.get("confusion_matrix", {})
    all_cols = sorted(list({col for r in conf.values() for col in r.keys()}))
    # Build markdown table for confusion matrix
    header = "| Expected \\ Predicted | " + " | ".join(f"`{c}`" for c in all_cols) + " |"
    sep = "|---|" + "---|" * len(all_cols)
    lines.append(header)
    lines.append(sep)
    for exp_cat, pred_dict in conf.items():
        row_vals = [str(pred_dict.get(col, 0)) for col in all_cols]
        lines.append(f"| `{exp_cat}` | " + " | ".join(row_vals) + " |")
    lines.append("")

    # 5. High-Confidence Errors
    lines.append("## 5. High-Confidence Errors (Confidence >= 0.90)")
    high_errs = c_metrics.get("high_confidence_wrong_samples", [])
    if not high_errs:
        lines.append("- *None observed in this dataset.*")
    else:
        for err in high_errs:
            lines.append(
                f"- **Case**: `{err['case_id']}` | **Appendix**: {err['appendix_number']} | **Image**: `{err['image_filename']}`\n"
                f"  - Expected: `{err['expected']}`\n"
                f"  - Predicted: `{err['predicted']}` (Confidence: {err['confidence']})"
            )
    lines.append("")

    # 6. OCR Failures
    lines.append("## 6. OCR Failures & Anchor Detection")
    ocr_cat_stats = ocr_results.get("category_anchor_stats", {})
    lines.append("| Category | Total Images | Key Anchors Detected | Key Anchors Missing |")
    lines.append("|---|---|---|---|")
    for cat, stat in ocr_cat_stats.items():
        tot_img = stat.get("total_images", 0)
        det_anchors = []
        miss_anchors = []
        for a_name, a_stat in stat.get("anchors", {}).items():
            if a_stat.get("missing", 0) > 0:
                miss_anchors.append(f"{a_name} ({a_stat['missing']} missed)")
            else:
                det_anchors.append(a_name)
        lines.append(
            f"| `{cat}` | {tot_img} | {', '.join(det_anchors) if det_anchors else 'None'} | {', '.join(miss_anchors) if miss_anchors else 'None'} |"
        )
    lines.append("")

    # 7. Field Extraction Accuracy
    lines.append("## 7. Field Extraction Accuracy")
    lines.append(f"- **Overall Field Extraction Accuracy**: **{round(extraction_results.get('overall_accuracy', 0.0) * 100, 2)}%**")
    lines.append("")
    lines.append("| Field | Tested | Correct | Incorrect | Missing | Accuracy | Root Cause Breakdown |")
    lines.append("|---|---|---|---|---|---|---|")
    for field_name, fdata in e_metrics.items():
        rc_str = ", ".join(f"{k}: {v}" for k, v in fdata.get("root_causes", {}).items()) or "None"
        lines.append(
            f"| `{field_name}` | {fdata['tested']} | {fdata['correct']} | {fdata['incorrect']} | {fdata['missing']} | {round(fdata['accuracy']*100, 1)}% | {rc_str} |"
        )
    lines.append("")

    # 8. Business Rule Evaluation Accuracy
    lines.append("## 8. Business Rule Evaluation Accuracy")
    lines.append("| Rule | Tested | Correct | Incorrect | Accuracy |")
    lines.append("|---|---|---|---|---|")
    for rule_name, rdata in r_metrics.items():
        lines.append(
            f"| `{rule_name}` | {rdata['tested']} | {rdata['correct']} | {rdata['incorrect']} | {round(rdata['accuracy']*100, 1)}% |"
        )
    lines.append("")

    # 9. Known Unsupported Cases
    lines.append("## 9. Known Unsupported Cases")
    lines.append("- `hardware.active_ports`: FortiGate interface active port count extraction is not yet modeled in the rule/extraction pipeline.")
    lines.append("- Multi-image dynamic interfaces (Appendix 3 with 4 screenshots) and routing tables (Appendix 7 with 5-7 screenshots) require aggregating interface link statuses across multiple pages.")
    lines.append("")

    # 10. Dataset Limitations
    lines.append("## 10. Dataset Limitations")
    lines.append("> [!IMPORTANT]")
    lines.append("> The screenshots in this dataset were extracted from completed FortiGate PM reports (`.docx`).")
    lines.append("> They may already be pre-cropped, resized, or compressed by the engineers.")
    lines.append("> Therefore, this dataset validates:")
    lines.append("> 1. Native Windows OCR text extraction on real FortiGate screenshots.")
    lines.append("> 2. Screenshot classification profiles against production screenshot text.")
    lines.append("> 3. Field extraction parsers against real FortiOS data formats.")
    lines.append("> 4. Business rule evaluation on real operational parameters.")
    lines.append("> It does **NOT** fully validate raw full-desktop screenshot auto-cropping, multi-monitor resolutions, or arbitrary unconstrained browser window captures.")
    lines.append("")

    # 11. Recommended Fixes / Hardening
    lines.append("## 11. Recommendations & Hardening Focus")
    if high_errs or c_metrics.get("incorrect", 0) > 0:
        lines.append("- Refine category anchor terms and negative penalties for categories experiencing misclassification.")
    lines.append("- Support alternative uptime string formats (e.g. `177 days 14 hours 24 minutes` in addition to `51 day(s) 3 hour(s) 44 min(s)`).")
    lines.append("- Align firmware build extraction format with integer build number (`2878` vs `build2878`).")
    lines.append("")

    return "\n".join(lines)
