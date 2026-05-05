"""Intervention policies for drift mitigation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from driftguard.ledger import regenerate_ledger_from_transcript
from driftguard.schemas import (
    CheckpointState,
    DriftAssessment,
    IntentContract,
    InterventionAction,
    MemoryState,
)


@dataclass
class BasePolicy:
    name: str

    def apply(
        self,
        contract: IntentContract,
        memory_state: MemoryState,
        assessment: DriftAssessment,
        checkpoints: List[CheckpointState],
    ) -> InterventionAction:
        raise NotImplementedError


class NoInterventionPolicy(BasePolicy):
    def __init__(self) -> None:
        super().__init__(name="none")

    def apply(
        self,
        contract: IntentContract,
        memory_state: MemoryState,
        assessment: DriftAssessment,
        checkpoints: List[CheckpointState],
    ) -> InterventionAction:
        return InterventionAction(action_type="none", applied=False, reason="policy_disabled")


class AnchorRefreshPolicy(BasePolicy):
    def __init__(self, threshold: float = 0.35) -> None:
        super().__init__(name="anchor_refresh")
        self.threshold = threshold

    def apply(
        self,
        contract: IntentContract,
        memory_state: MemoryState,
        assessment: DriftAssessment,
        checkpoints: List[CheckpointState],
    ) -> InterventionAction:
        if assessment.overall_score < self.threshold:
            return InterventionAction(action_type="anchor_refresh", applied=False, reason="score_below_threshold")
        memory_state.anchors = list(contract.hard_constraints)
        return InterventionAction(
            action_type="anchor_refresh",
            applied=True,
            reason="constraints_reinjected",
            payload={"anchors": list(memory_state.anchors)},
        )


class LedgerRegenerationPolicy(BasePolicy):
    def __init__(self, threshold: float = 0.5) -> None:
        super().__init__(name="ledger_regeneration")
        self.threshold = threshold

    def apply(
        self,
        contract: IntentContract,
        memory_state: MemoryState,
        assessment: DriftAssessment,
        checkpoints: List[CheckpointState],
    ) -> InterventionAction:
        if assessment.overall_score < self.threshold:
            return InterventionAction(action_type="ledger_regeneration", applied=False, reason="score_below_threshold")
        memory_state.ledger = regenerate_ledger_from_transcript(contract, memory_state.transcript_events)
        return InterventionAction(action_type="ledger_regeneration", applied=True, reason="ledger_rebuilt")


class RollbackPolicy(BasePolicy):
    def __init__(self, threshold: float = 0.8) -> None:
        super().__init__(name="rollback")
        self.threshold = threshold

    def apply(
        self,
        contract: IntentContract,
        memory_state: MemoryState,
        assessment: DriftAssessment,
        checkpoints: List[CheckpointState],
    ) -> InterventionAction:
        if assessment.overall_score < self.threshold or not checkpoints:
            return InterventionAction(action_type="rollback", applied=False, reason="rollback_not_triggered")
        checkpoint = checkpoints[-1]
        restored = checkpoint.memory_state.clone()
        memory_state.transcript_events = restored.transcript_events
        memory_state.summary_notes = restored.summary_notes
        memory_state.ledger = restored.ledger
        memory_state.retrieval_cache = restored.retrieval_cache
        memory_state.anchors = restored.anchors
        return InterventionAction(
            action_type="rollback",
            applied=True,
            reason="restored_last_good_checkpoint",
            target_checkpoint_id=checkpoint.checkpoint_id,
        )


class SafeStopPolicy(BasePolicy):
    def __init__(self, threshold: float = 0.9) -> None:
        super().__init__(name="safe_stop")
        self.threshold = threshold

    def apply(
        self,
        contract: IntentContract,
        memory_state: MemoryState,
        assessment: DriftAssessment,
        checkpoints: List[CheckpointState],
    ) -> InterventionAction:
        if assessment.overall_score < self.threshold:
            return InterventionAction(action_type="safe_stop", applied=False, reason="score_below_threshold")
        return InterventionAction(action_type="safe_stop", applied=True, reason="unsafe_to_continue", payload={"stop": True})


class AdaptivePolicy(BasePolicy):
    def __init__(self) -> None:
        super().__init__(name="adaptive")
        self.anchor = AnchorRefreshPolicy()
        self.regenerate = LedgerRegenerationPolicy()
        self.rollback = RollbackPolicy()
        self.safe_stop = SafeStopPolicy()

    def apply(
        self,
        contract: IntentContract,
        memory_state: MemoryState,
        assessment: DriftAssessment,
        checkpoints: List[CheckpointState],
    ) -> InterventionAction:
        if assessment.overall_score >= 0.9:
            return self.safe_stop.apply(contract, memory_state, assessment, checkpoints)
        if assessment.overall_score >= 0.75:
            return self.rollback.apply(contract, memory_state, assessment, checkpoints)
        if assessment.overall_score >= 0.5:
            return self.regenerate.apply(contract, memory_state, assessment, checkpoints)
        if assessment.overall_score >= 0.35:
            return self.anchor.apply(contract, memory_state, assessment, checkpoints)
        return InterventionAction(action_type="adaptive", applied=False, reason="no_action_needed")


ALL_POLICIES = {
    policy.name: policy
    for policy in (
        NoInterventionPolicy(),
        AnchorRefreshPolicy(),
        LedgerRegenerationPolicy(),
        RollbackPolicy(),
        SafeStopPolicy(),
        AdaptivePolicy(),
    )
}
