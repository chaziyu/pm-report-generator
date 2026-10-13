"""
Pipeline Evaluator for PM Report Dataset.
Coordinates end-to-end evaluation of:
  Screenshot Image -> Normalization -> OCR -> Classification -> Extraction -> Rules
Saves machine-readable JSON artifacts and human-readable Markdown reports.
"""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

from ...models.screenshot import ScreenshotRecord, OCRToken
from ..image.processor import normalize_image
from ..ocr.service import ocr_service
from ..ai.service import local_ai_service
from ..ai.schemas import ArbitrationState
from .classifier_evaluator import classifier_evaluator, APPENDIX_TO_CATEGORY
from .extraction_evaluator import extraction_evaluator, EVALUATED_FIELDS, EVALUATED_RULES
from .ocr_evaluator import ocr_evaluator, CATEGORY_ANCHORS
from .metrics import (
    compute_classification_metrics,
    compute_extraction_metrics,
    compute_rule_metrics,
    compute_performance_metrics,
    compute_ai_metrics,
)
from .report import generate_markdown_report

class PipelineEvaluator:
    """
    Evaluates the complete PM Report generation pipeline against an imported historical dataset.
    """

    def __init__(self, dataset_dir: Path, output_dir: Path, cache_dir: Optional[Path] = None):
        self.dataset_dir = Path(dataset_dir)
        self.output_dir = Path(output_dir)
        self.cache_dir = Path(cache_dir) if cache_dir else self.output_dir / ".cache"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def run_evaluation(self, mode: str = "baseline") -> Dict[str, Any]:
        """
        Executes full evaluation on dataset_dir and saves outputs to output_dir.
        Mode can be 'baseline' or 'after_hardening'.
        """
        dataset_index_path = self.dataset_dir / "dataset.json"
        if not dataset_index_path.exists():
            raise FileNotFoundError(f"dataset.json not found in {self.dataset_dir}")

        with open(dataset_index_path, "r", encoding="utf-8") as f:
            dataset_index = json.load(f)

        cases = dataset_index.get("cases", [])

        all_image_records: List[Dict[str, Any]] = []
        all_ocr_records: List[Dict[str, Any]] = []
        all_image_durations: List[Dict[str, float]] = []
        all_case_extractions: List[Dict[str, Any]] = []

        total_cases_evaluated = 0
        total_images_evaluated = 0

        for case_entry in cases:
            case_id = case_entry["case_id"]
            case_dir = self.dataset_dir / case_id
            manifest_path = case_dir / "manifest.json"
            expected_path = case_dir / "expected.json"
            appendices_dir = case_dir / "appendices"

            if not (manifest_path.exists() and expected_path.exists() and appendices_dir.exists()):
                continue

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)

            if manifest.get("template_variant") != "fortigate_pm_v1":
                # Section 4: Do not include unsupported template variants in metrics
                continue

            with open(expected_path, "r", encoding="utf-8") as f:
                expected = json.load(f)

            total_cases_evaluated += 1

            case_screenshots: List[ScreenshotRecord] = []

            # Evaluate each appendix image in order
            for app_num_str in sorted(manifest.get("appendices", {}).keys(), key=int):
                app_num = int(app_num_str)
                app_info = manifest["appendices"][app_num_str]
                image_names = app_info.get("images", [])

                for idx, img_name in enumerate(image_names, start=1):
                    img_path = appendices_dir / img_name
                    if not img_path.exists():
                        continue

                    total_images_evaluated += 1
                    t_start = time.perf_counter()

                    # 1. Normalization
                    norm_dir = self.cache_dir / case_id
                    norm_path = norm_dir / f"norm_{img_name}"
                    t_norm_start = time.perf_counter()
                    w, h = normalize_image(img_path, norm_path)
                    t_norm_ms = round((time.perf_counter() - t_norm_start) * 1000, 2)

                    # 2. OCR
                    t_ocr_start = time.perf_counter()
                    tokens, ocr_text = ocr_service.process_image(norm_path)
                    t_ocr_ms = round((time.perf_counter() - t_ocr_start) * 1000, 2)

                    # 3. Create ScreenshotRecord
                    sc_record = ScreenshotRecord(
                        id=f"{case_id}_{app_num:02d}_{idx:02d}",
                        filename=img_name,
                        original_path=str(img_path),
                        normalized_path=str(norm_path),
                        width=w,
                        height=h,
                        ocr_tokens=tokens,
                        ocr_text=ocr_text,
                    )

                    source_caption = app_info.get("title")
                    is_canonical = (manifest.get("is_verified_canonical", False) or case_id in ("case_0387ca989c_fortigate_200f", "case_b1cf0925e5_fortigate_201f"))

                    # 4. Classification
                    t_cls_start = time.perf_counter()
                    cls_eval = classifier_evaluator.evaluate_screenshot(
                        case_id=case_id,
                        appendix_number=app_num,
                        image_index=idx,
                        image_filename=img_name,
                        screenshot=sc_record,
                        source_caption=source_caption,
                        is_verified_canonical=is_canonical,
                    )
                    t_cls_ms = round((time.perf_counter() - t_cls_start) * 1000, 2)

                    # 4.1 AI Fallback (if deterministic_plus_ai)
                    exp_cat = cls_eval["expected_category"]
                    if mode == "deterministic_plus_ai":
                        amb = local_ai_service.check_ambiguity(sc_record)
                        arb_state, assigned_cats, prov = local_ai_service.verify_classification(
                            screenshot=sc_record,
                            deterministic_category=cls_eval["predicted_category"],
                            deterministic_confidence=cls_eval["confidence"],
                        )
                        ai_invoked = prov is not None
                        cls_eval["ai_invoked"] = ai_invoked
                        cls_eval["is_ambiguous"] = amb.ambiguous
                        cls_eval["ambiguity_reasons"] = amb.reasons
                        cls_eval["arbitration_state"] = arb_state.value
                        cls_eval["ai_latency_ms"] = prov.processing_time_ms if prov else 0.0

                        evidenced = []
                        if prov and prov.ai_result and "categories" in prov.ai_result:
                            evidenced = [c["category"] for c in prov.ai_result["categories"] if c.get("evidenced", False)]
                        cls_eval["multi_category_evidenced"] = evidenced
                        cls_eval["multi_category_match"] = (exp_cat in evidenced) if evidenced else (cls_eval["predicted_category"] == exp_cat)
                        cls_eval["assigned_categories"] = assigned_cats
                        cls_eval["ai_provenance"] = prov.dict() if prov else None
                        sc_record.assigned_categories = assigned_cats
                        if arb_state in [ArbitrationState.REVIEW_REQUIRED, ArbitrationState.DISAGREEMENT]:
                            cls_eval["review_status"] = "REVIEW_REQUIRED"
                    else:
                        cls_eval["ai_invoked"] = False
                        cls_eval["is_ambiguous"] = False
                        cls_eval["ambiguity_reasons"] = []
                        cls_eval["arbitration_state"] = "DETERMINISTIC_ACCEPTED"
                        cls_eval["ai_latency_ms"] = 0.0
                        cls_eval["multi_category_evidenced"] = []
                        cls_eval["multi_category_match"] = cls_eval["correct"]

                    # 5. OCR Anchor evaluation
                    ocr_eval = ocr_evaluator.evaluate_tokens(tokens, ocr_text, exp_cat)

                    t_total_ms = round((time.perf_counter() - t_start) * 1000, 2)

                    # Record timing
                    all_image_durations.append({
                        "image": f"{case_id}/{img_name}",
                        "normalization_ms": t_norm_ms,
                        "ocr_ms": t_ocr_ms,
                        "classification_ms": t_cls_ms,
                        "total_ms": t_total_ms,
                    })

                    # Record classification record
                    cls_eval["normalization_time_ms"] = t_norm_ms
                    cls_eval["ocr_time_ms"] = t_ocr_ms
                    cls_eval["total_time_ms"] = t_total_ms
                    cls_eval["processing_time_ms"] = t_total_ms
                    all_image_records.append(cls_eval)

                    # Record OCR record
                    all_ocr_records.append({
                        "case_id": case_id,
                        "appendix_number": app_num,
                        "image_filename": img_name,
                        "expected_category": exp_cat,
                        "anchors_found": ocr_eval["found_anchors"],
                        "anchors_missing": ocr_eval["missing_anchors"],
                        "token_count": ocr_eval["token_count"],
                        "avg_token_confidence": ocr_eval["avg_confidence"],
                        "ocr_time_ms": t_ocr_ms,
                    })

                    case_screenshots.append(sc_record)

            # 6. Extraction for this case
            case_extract = extraction_evaluator.evaluate_case(
                case_id=case_id,
                screenshots=case_screenshots,
                expected=expected,
                manifest=manifest,
            )
            all_case_extractions.append(case_extract)

        # Compute Metrics
        all_categories = list(APPENDIX_TO_CATEGORY.values())
        classification_metrics = compute_classification_metrics(all_image_records, all_categories)
        extraction_metrics = compute_extraction_metrics(all_case_extractions, EVALUATED_FIELDS)
        rule_metrics = compute_rule_metrics(all_case_extractions, EVALUATED_RULES)
        performance_metrics = compute_performance_metrics(all_image_durations)
        ai_metrics = compute_ai_metrics(all_image_records)

        # Aggregate OCR anchor stats
        ocr_category_stats: Dict[str, Dict[str, Any]] = {}
        for r in all_ocr_records:
            cat = r["expected_category"]
            if cat not in ocr_category_stats:
                ocr_category_stats[cat] = {
                    "total_images": 0,
                    "anchors": {a: {"found": 0, "missing": 0} for a in CATEGORY_ANCHORS.get(cat, [])},
                }
            ocr_category_stats[cat]["total_images"] += 1
            for a in r["anchors_found"]:
                if a in ocr_category_stats[cat]["anchors"]:
                    ocr_category_stats[cat]["anchors"][a]["found"] += 1
            for a in r["anchors_missing"]:
                if a in ocr_category_stats[cat]["anchors"]:
                    ocr_category_stats[cat]["anchors"][a]["missing"] += 1

        # Build output objects
        classifier_results = {
            "metrics": classification_metrics,
            "ai_metrics": ai_metrics,
            "records": all_image_records,
        }

        extraction_results = {
            "overall_accuracy": extraction_metrics["overall_accuracy"],
            "total_fields_tested": extraction_metrics["total_fields_tested"],
            "total_fields_correct": extraction_metrics["total_fields_correct"],
            "fields": extraction_metrics["fields"],
            "rules": rule_metrics,
            "cases": all_case_extractions,
        }

        ocr_results = {
            "total_images": len(all_ocr_records),
            "category_anchor_stats": ocr_category_stats,
            "records": all_ocr_records,
        }

        evaluation_summary = {
            "dataset": {
                "cases": total_cases_evaluated,
                "images": total_images_evaluated,
            },
            "classification": {
                "total_images": classification_metrics["total"],
                "correct": classification_metrics["correct"],
                "accuracy": classification_metrics["accuracy"],
                "high_confidence_wrong": classification_metrics["high_confidence_wrong_count"],
                "medium_confidence_wrong": classification_metrics["medium_confidence_wrong_count"],
                "unknown_rate": classification_metrics["unknown_rate"],
            },
            "ai": ai_metrics,
            "extraction": {
                f: {
                    "tested": extraction_metrics["fields"][f]["tested"],
                    "correct": extraction_metrics["fields"][f]["correct"],
                    "accuracy": extraction_metrics["fields"][f]["accuracy"],
                }
                for f in extraction_metrics["fields"]
            },
            "rules": rule_metrics,
            "ocr": {
                "total_images": len(all_ocr_records),
            },
            "performance": performance_metrics,
        }

        pipeline_results = {
            "summary": evaluation_summary,
            "durations": all_image_durations,
        }

        # Save to target output directory
        self._save_json(self.output_dir / "classifier_results.json", classifier_results)
        self._save_json(self.output_dir / "extraction_results.json", extraction_results)
        self._save_json(self.output_dir / "ocr_results.json", ocr_results)
        self._save_json(self.output_dir / "pipeline_results.json", pipeline_results)
        self._save_json(self.output_dir / "evaluation_summary.json", evaluation_summary)

        # Generate markdown report
        md_report = generate_markdown_report(
            summary=evaluation_summary,
            classifier_results=classifier_results,
            extraction_results=extraction_results,
            ocr_results=ocr_results,
            pipeline_results=pipeline_results,
            mode=mode,
        )
        report_path = self.output_dir / "evaluation_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_report)

        # If mode is 'baseline' or 'after_hardening', also preserve in subfolder
        subfolder = self.output_dir / mode
        subfolder.mkdir(parents=True, exist_ok=True)
        self._save_json(subfolder / "classifier_results.json", classifier_results)
        self._save_json(subfolder / "extraction_results.json", extraction_results)
        self._save_json(subfolder / "ocr_results.json", ocr_results)
        self._save_json(subfolder / "pipeline_results.json", pipeline_results)
        self._save_json(subfolder / "evaluation_summary.json", evaluation_summary)
        with open(subfolder / "evaluation_report.md", "w", encoding="utf-8") as f:
            f.write(md_report)

        return evaluation_summary

    def _save_json(self, path: Path, data: Any):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
