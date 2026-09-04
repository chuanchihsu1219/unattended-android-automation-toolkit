from __future__ import annotations

import traceback
import uuid
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Protocol

from .evidence import EvidenceWriter, create_evidence_directory
from .models import MetricSnapshot, PipelineOutcome, ProductRule, RangeRule
from .security import SecretRedactor
from .storage import ObservationStore
from .validation import validate_snapshot


class ManagedDevice(Protocol):
    def start(self) -> None: ...

    def shutdown(self) -> None: ...


class AppAdapter(Protocol):
    name: str

    def collect(self, device: ManagedDevice) -> MetricSnapshot: ...


class CollectionPipeline:
    def __init__(
        self,
        *,
        store: ObservationStore,
        evidence_root: Path,
        device_factory: Callable[[EvidenceWriter], ManagedDevice],
        adapter: AppAdapter,
        range_rules: Iterable[RangeRule] = (),
        product_rules: Iterable[ProductRule] = (),
        redactor: SecretRedactor | None = None,
    ) -> None:
        self.store = store
        self.evidence_root = evidence_root
        self.device_factory = device_factory
        self.adapter = adapter
        self.range_rules = tuple(range_rules)
        self.product_rules = tuple(product_rules)
        self.redactor = redactor or SecretRedactor()

    def run(self) -> PipelineOutcome:
        run_id = str(uuid.uuid4())
        evidence_path = create_evidence_directory(self.evidence_root, run_id)
        evidence = EvidenceWriter(evidence_path, self.redactor)
        self.store.begin_run(run_id, evidence_path)
        device = self.device_factory(evidence)
        outcome: PipelineOutcome
        evidence.log("run_started", run_id=run_id, adapter=self.adapter.name)
        try:
            device.start()
            snapshot = self.adapter.collect(device)
            evidence.write_json("extraction.json", snapshot.as_dict())
            validation = validate_snapshot(
                snapshot,
                range_rules=self.range_rules,
                product_rules=self.product_rules,
            )
            evidence.write_json("validation.json", validation.as_dict())
            if not validation.passed:
                error = "; ".join(validation.errors)
                self.store.finish_run(run_id, "REJECTED", error)
                outcome = PipelineOutcome(run_id=run_id, status="REJECTED", error=error)
            else:
                observation_id, inserted = self.store.insert_first_validated(snapshot, run_id)
                self.store.finish_run(run_id, "SUCCESS")
                outcome = PipelineOutcome(
                    run_id=run_id,
                    status="SUCCESS",
                    inserted=inserted,
                    observation_id=observation_id,
                )
        except Exception as error:
            safe_error = self.redactor.text(error)
            evidence.write_text("traceback.txt", traceback.format_exc())
            self.store.finish_run(run_id, "FAILED", safe_error)
            outcome = PipelineOutcome(run_id=run_id, status="FAILED", error=safe_error)
        finally:
            try:
                device.shutdown()
            except Exception as cleanup_error:
                evidence.log("cleanup_failed", error=self.redactor.text(cleanup_error))
        evidence.write_json("result.json", outcome.as_dict())
        evidence.log("run_finished", status=outcome.status)
        return outcome
