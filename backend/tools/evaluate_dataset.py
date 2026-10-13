"""
CLI Tool for Dataset-Driven Pipeline Evaluation.
Usage:
    python backend/tools/evaluate_dataset.py [--dataset PATH] [--output PATH] [--mode baseline|after_hardening]
"""

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.evaluation.pipeline_evaluator import PipelineEvaluator

def main():
    parser = argparse.ArgumentParser(description="Evaluate PM Report pipeline against historical ground truth.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="workspace/datasets/pm_reports",
        help="Path to the dataset directory containing dataset.json and case folders",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="workspace/evaluation",
        help="Path to save evaluation JSON artifacts and report",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["baseline", "after_hardening", "deterministic", "deterministic_plus_ai"],
        default="deterministic",
        help="Evaluation run mode: 'baseline', 'after_hardening', 'deterministic', or 'deterministic_plus_ai'",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Optional directory to cache normalized images",
    )
    parser.add_argument(
        "--mock-ai",
        action="store_true",
        help="Use FakeAIProvider for local AI simulation testing",
    )

    args = parser.parse_args()

    if args.mock_ai:
        from app.services.ai.base import FakeAIProvider
        from app.services.ai.service import local_ai_service
        local_ai_service.set_provider(FakeAIProvider())

    dataset_path = Path(args.dataset).resolve()
    output_path = Path(args.output).resolve()
    cache_path = Path(args.cache_dir).resolve() if args.cache_dir else None

    print("=" * 70)
    print(f"PM REPORT PIPELINE EVALUATION ({args.mode.upper()})")
    print(f"Dataset path: {dataset_path}")
    print(f"Output path:  {output_path}")
    print("=" * 70)

    evaluator = PipelineEvaluator(
        dataset_dir=dataset_path,
        output_dir=output_path,
        cache_dir=cache_path,
    )

    try:
        summary = evaluator.run_evaluation(mode=args.mode)
    finally:
        if not args.mock_ai:
            try:
                from app.services.ai.service import local_ai_service
                if local_ai_service.runtime_manager.is_running:
                    local_ai_service.runtime_manager.shutdown()
            except Exception:
                pass

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"Cases Evaluated:      {summary['dataset']['cases']}")
    print(f"Images Evaluated:     {summary['dataset']['images']}")
    print(f"Classification Acc:   {round(summary['classification']['accuracy'] * 100, 2)}% ({summary['classification']['correct']}/{summary['classification']['total_images']})")
    print(f"High-Conf Wrong:      {summary['classification']['high_confidence_wrong']}")
    print(f"Unknown Rate:         {round(summary['classification']['unknown_rate'] * 100, 2)}%")

    if "ai" in summary and (args.mode == "deterministic_plus_ai" or summary["ai"].get("ai_invocations", 0) > 0):
        ai = summary["ai"]
        print("-" * 70)
        print("LOCAL AI FALLBACK & ARBITRATION METRICS")
        print(f"AI Invocations:       {ai['ai_invocations']} ({round(ai['ai_invocation_rate'] * 100, 2)}%)")
        print(f"AI Agreement Rate:    {round(ai['ai_agreement_rate'] * 100, 2)}% ({ai['ai_agreements']} agreements)")
        print(f"AI Disagreement Rate: {round(ai['ai_disagreement_rate'] * 100, 2)}% ({ai['ai_disagreements']} disagreements)")
        print(f"Multi-Category Match: {round(ai['multi_category_evidence_accuracy'] * 100, 2)}% ({ai['multi_category_count']} ambiguous screenshots)")
        print(f"Manual Review Rate:   {round(ai['manual_review_rate'] * 100, 2)}% ({ai['manual_review_count']} items flagged)")
        print(f"AI Processing Time:   avg {ai['latency']['avg_ms']} ms | max {ai['latency']['max_ms']} ms")

    print("-" * 70)
    print(f"Avg Image Time:       {summary['performance']['avg_image_duration_ms']} ms")
    print(f"Total Pipeline Time:  {summary['performance']['total_duration_ms']} ms")
    print("=" * 70)
    print(f"Report saved to: {output_path / 'evaluation_report.md'}")
    print(f"Results saved to: {output_path / mode_subfolder(args.mode)}")
    print("=" * 70)

def mode_subfolder(mode: str) -> str:
    return f"{mode}/"

if __name__ == "__main__":
    main()
