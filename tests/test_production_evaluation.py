from evaluation.production import evaluate, retrieval_metrics


def test_out_of_scope_failure_is_not_automatic_success():
    metrics = retrieval_metrics(["irrelevant act"], [], out_of_scope=True)
    assert metrics["rejection_correct"] is False
    assert metrics["recall_at_k"] is None
    assert retrieval_metrics([], [], out_of_scope=True)["rejection_correct"] is True


def test_exact_retrieval_metrics():
    metrics = retrieval_metrics(["wrong", "A", "A"], ["A", "B"])
    assert metrics["recall_at_k"] == 0.5
    assert metrics["precision_at_k"] == 0.5
    assert metrics["mrr"] == 0.5


def test_missing_labels_not_scored_as_perfect():
    assert retrieval_metrics(["A"], [])["recall_at_k"] is None


def test_errors_remain_in_report_denominator():
    class Pipeline:
        def query(self, *args, **kwargs):
            raise RuntimeError("offline")

    report = evaluate([{"id": "one", "question": "question"}], Pipeline())
    assert report["n"] == report["failures"] == 1
    assert report["claim_accuracy"] is None
