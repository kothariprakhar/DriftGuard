"""Typed schemas for DriftGuard benchmark execution."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _require_non_empty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


@dataclass
class BudgetCeiling:
    max_steps: int
    max_visible_items: int
    max_tool_calls: int

    def validate(self) -> None:
        _require_non_negative("max_steps", self.max_steps)
        _require_non_negative("max_visible_items", self.max_visible_items)
        _require_non_negative("max_tool_calls", self.max_tool_calls)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetCeiling":
        budget = cls(**data)
        budget.validate()
        return budget

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class IntentContract:
    task_statement: str
    success_criteria: List[str]
    hard_constraints: List[str]
    soft_preferences: List[str]
    forbidden_actions: List[str]
    allowed_scope_expansions: List[str]
    evidence_requirements: List[str]
    stop_conditions: List[str]
    version: str

    def validate(self) -> None:
        _require_non_empty("task_statement", self.task_statement)
        _require_non_empty("version", self.version)
        if not self.success_criteria:
            raise ValueError("success_criteria must not be empty")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentContract":
        contract = cls(**data)
        contract.validate()
        return contract

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class LedgerItem:
    item_id: str
    kind: str
    status: str
    content: str
    source_step_ids: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0
    created_at: str = ""
    updated_at: str = ""

    def validate(self) -> None:
        _require_non_empty("item_id", self.item_id)
        _require_non_empty("kind", self.kind)
        _require_non_empty("status", self.status)
        _require_non_empty("content", self.content)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerItem":
        item = cls(**data)
        item.validate()
        return item

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class StateLedger:
    facts: List[LedgerItem] = field(default_factory=list)
    constraints: List[LedgerItem] = field(default_factory=list)
    decisions: List[LedgerItem] = field(default_factory=list)
    outstanding_work: List[LedgerItem] = field(default_factory=list)
    plan_steps: List[LedgerItem] = field(default_factory=list)
    accepted_evidence: List[LedgerItem] = field(default_factory=list)
    assumptions: List[LedgerItem] = field(default_factory=list)
    open_questions: List[LedgerItem] = field(default_factory=list)
    rejected_paths: List[LedgerItem] = field(default_factory=list)
    risk_flags: List[LedgerItem] = field(default_factory=list)
    active_subgoal: str = ""

    BUCKETS = (
        "facts",
        "constraints",
        "decisions",
        "outstanding_work",
        "plan_steps",
        "accepted_evidence",
        "assumptions",
        "open_questions",
        "rejected_paths",
        "risk_flags",
    )

    def validate(self) -> None:
        for bucket in self.BUCKETS:
            for item in getattr(self, bucket):
                item.validate()

    def clone(self) -> "StateLedger":
        return StateLedger.from_dict(self.to_dict())

    def add_item(self, bucket: str, item: LedgerItem) -> None:
        if bucket not in self.BUCKETS:
            raise ValueError(f"unknown ledger bucket: {bucket}")
        item.validate()
        getattr(self, bucket).append(item)

    def replace_bucket(self, bucket: str, items: List[LedgerItem]) -> None:
        if bucket not in self.BUCKETS:
            raise ValueError(f"unknown ledger bucket: {bucket}")
        setattr(self, bucket, items)

    def all_items(self) -> List[LedgerItem]:
        items: List[LedgerItem] = []
        for bucket in self.BUCKETS:
            items.extend(getattr(self, bucket))
        return items

    def find_contents(self, bucket: str) -> List[str]:
        if bucket not in self.BUCKETS:
            raise ValueError(f"unknown ledger bucket: {bucket}")
        return [item.content for item in getattr(self, bucket)]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateLedger":
        kwargs: Dict[str, Any] = {"active_subgoal": data.get("active_subgoal", "")}
        for bucket in cls.BUCKETS:
            kwargs[bucket] = [LedgerItem.from_dict(item) for item in data.get(bucket, [])]
        ledger = cls(**kwargs)
        ledger.validate()
        return ledger

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        result: Dict[str, Any] = {"active_subgoal": self.active_subgoal}
        for bucket in self.BUCKETS:
            result[bucket] = [item.to_dict() for item in getattr(self, bucket)]
        return result


@dataclass
class VisibleState:
    visible_constraints: List[str]
    visible_evidence_ids: List[str]
    visible_decisions: List[str]
    visible_events: List[str]
    summary_notes: List[str]
    active_subgoal: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisibleState":
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryState:
    transcript_events: List[Dict[str, Any]] = field(default_factory=list)
    summary_notes: List[str] = field(default_factory=list)
    ledger: StateLedger = field(default_factory=StateLedger)
    retrieval_cache: List[str] = field(default_factory=list)
    anchors: List[str] = field(default_factory=list)

    def clone(self) -> "MemoryState":
        return MemoryState.from_dict(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryState":
        return cls(
            transcript_events=data.get("transcript_events", []),
            summary_notes=data.get("summary_notes", []),
            ledger=StateLedger.from_dict(data.get("ledger", {})),
            retrieval_cache=data.get("retrieval_cache", []),
            anchors=data.get("anchors", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transcript_events": list(self.transcript_events),
            "summary_notes": list(self.summary_notes),
            "ledger": self.ledger.to_dict(),
            "retrieval_cache": list(self.retrieval_cache),
            "anchors": list(self.anchors),
        }


@dataclass
class DecisionOption:
    option_id: str
    label: str
    appeal: int
    supports_goal: bool
    supported_by: List[str]
    violates_constraints: List[str]
    evidence_to_accept: List[str] = field(default_factory=list)
    ledger_updates: Dict[str, List[str]] = field(default_factory=dict)
    drift_label_if_chosen: Optional[str] = None

    def validate(self) -> None:
        _require_non_empty("option_id", self.option_id)
        _require_non_empty("label", self.label)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionOption":
        option = cls(**data)
        option.validate()
        return option

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class ScenarioEvent:
    event_id: str
    kind: str
    text: str
    salience: int
    payload: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _require_non_empty("event_id", self.event_id)
        _require_non_empty("kind", self.kind)
        _require_non_empty("text", self.text)
        _require_non_negative("salience", self.salience)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioEvent":
        event = cls(**data)
        event.validate()
        return event

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class ProvenanceRequirement:
    bucket: str
    content: str
    evidence_ids: List[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty("bucket", self.bucket)
        _require_non_empty("content", self.content)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProvenanceRequirement":
        requirement = cls(**data)
        requirement.validate()
        return requirement

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class GoldCheckpoint:
    checkpoint_id: str
    after_event_id: str
    required_constraints: List[str]
    required_evidence_ids: List[str]
    required_decisions: List[str]
    forbidden_drift_labels: List[str]
    required_fact_contents: List[str] = field(default_factory=list)
    required_ledger_decisions: List[str] = field(default_factory=list)
    required_outstanding_work: List[str] = field(default_factory=list)
    required_plan_steps: List[str] = field(default_factory=list)
    required_accepted_evidence_ids: List[str] = field(default_factory=list)
    required_risk_flags: List[str] = field(default_factory=list)
    required_assumptions: List[str] = field(default_factory=list)
    required_active_subgoal: str = ""
    required_provenance: List[ProvenanceRequirement] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty("checkpoint_id", self.checkpoint_id)
        _require_non_empty("after_event_id", self.after_event_id)
        for requirement in self.required_provenance:
            requirement.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoldCheckpoint":
        checkpoint = cls(
            checkpoint_id=data["checkpoint_id"],
            after_event_id=data["after_event_id"],
            required_constraints=data.get("required_constraints", []),
            required_evidence_ids=data.get("required_evidence_ids", []),
            required_decisions=data.get("required_decisions", []),
            forbidden_drift_labels=data.get("forbidden_drift_labels", []),
            required_fact_contents=data.get("required_fact_contents", []),
            required_ledger_decisions=data.get("required_ledger_decisions", []),
            required_outstanding_work=data.get("required_outstanding_work", []),
            required_plan_steps=data.get("required_plan_steps", []),
            required_accepted_evidence_ids=data.get("required_accepted_evidence_ids", []),
            required_risk_flags=data.get("required_risk_flags", []),
            required_assumptions=data.get("required_assumptions", []),
            required_active_subgoal=data.get("required_active_subgoal", ""),
            required_provenance=[
                ProvenanceRequirement.from_dict(item) for item in data.get("required_provenance", [])
            ],
        )
        checkpoint.validate()
        return checkpoint

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "checkpoint_id": self.checkpoint_id,
            "after_event_id": self.after_event_id,
            "required_constraints": list(self.required_constraints),
            "required_evidence_ids": list(self.required_evidence_ids),
            "required_decisions": list(self.required_decisions),
            "forbidden_drift_labels": list(self.forbidden_drift_labels),
            "required_fact_contents": list(self.required_fact_contents),
            "required_ledger_decisions": list(self.required_ledger_decisions),
            "required_outstanding_work": list(self.required_outstanding_work),
            "required_plan_steps": list(self.required_plan_steps),
            "required_accepted_evidence_ids": list(self.required_accepted_evidence_ids),
            "required_risk_flags": list(self.required_risk_flags),
            "required_assumptions": list(self.required_assumptions),
            "required_active_subgoal": self.required_active_subgoal,
            "required_provenance": [item.to_dict() for item in self.required_provenance],
        }

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class ResourceProfile:
    version: str
    name: str
    transcript_capacity: int
    summary_capacity: int
    retrieval_k: int
    max_steps: int
    max_visible_events: int
    seed: int

    def validate(self) -> None:
        _require_non_empty("version", self.version)
        _require_non_empty("name", self.name)
        _require_non_negative("transcript_capacity", self.transcript_capacity)
        _require_non_negative("summary_capacity", self.summary_capacity)
        _require_non_negative("retrieval_k", self.retrieval_k)
        _require_non_negative("max_steps", self.max_steps)
        _require_non_negative("max_visible_events", self.max_visible_events)
        _require_non_negative("seed", self.seed)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceProfile":
        profile = cls(**data)
        profile.validate()
        return profile

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class PromptPack:
    version: str
    prompts: Dict[str, str]

    def validate(self) -> None:
        _require_non_empty("version", self.version)
        required = {
            "base_agent",
            "ledger_update",
            "summary_update",
            "retrieval_query",
            "detector_rubric",
            "trace_grader",
            "outcome_grader",
        }
        missing = required.difference(self.prompts)
        if missing:
            raise ValueError(f"prompt pack missing prompts: {sorted(missing)}")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptPack":
        pack = cls(**data)
        pack.validate()
        return pack

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)

    def get_prompt(self, name: str) -> str:
        self.validate()
        if name not in self.prompts:
            raise KeyError(f"unknown prompt name: {name}")
        return self.prompts[name]


@dataclass
class PerturbationCase:
    perturbation_id: str
    scenario_id: str
    context_system: str
    detector: str
    target_event_id: str
    perturbation_kind: str
    params: Dict[str, Any] = field(default_factory=dict)
    expected_min_score: float = 0.0
    expected_reason_codes: List[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty("perturbation_id", self.perturbation_id)
        _require_non_empty("scenario_id", self.scenario_id)
        _require_non_empty("context_system", self.context_system)
        _require_non_empty("detector", self.detector)
        _require_non_empty("target_event_id", self.target_event_id)
        _require_non_empty("perturbation_kind", self.perturbation_kind)
        if not 0.0 <= self.expected_min_score <= 1.0:
            raise ValueError("expected_min_score must be between 0 and 1")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerturbationCase":
        case = cls(**data)
        case.validate()
        return case

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class PerturbationSuite:
    name: str
    purpose: str
    cases: List[PerturbationCase]

    def validate(self) -> None:
        _require_non_empty("name", self.name)
        _require_non_empty("purpose", self.purpose)
        if not self.cases:
            raise ValueError("perturbation suite must include at least one case")
        for case in self.cases:
            case.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerturbationSuite":
        suite = cls(
            name=data["name"],
            purpose=data["purpose"],
            cases=[PerturbationCase.from_dict(item) for item in data.get("cases", [])],
        )
        suite.validate()
        return suite

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "name": self.name,
            "purpose": self.purpose,
            "cases": [case.to_dict() for case in self.cases],
        }


@dataclass
class AnnotationCase:
    example_id: str
    scenario_id: str
    focus: str
    preferred_context_systems: List[str] = field(default_factory=list)
    preferred_policies: List[str] = field(default_factory=list)
    preferred_detectors: List[str] = field(default_factory=list)
    preferred_seed: Optional[int] = None
    expected_primary_drift_label: str = ""
    expected_earliest_drift_step: str = ""
    expected_severity: str = ""
    expected_recoverable: Optional[bool] = None
    expected_final_success: Optional[bool] = None
    notes: List[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty("example_id", self.example_id)
        _require_non_empty("scenario_id", self.scenario_id)
        _require_non_empty("focus", self.focus)
        if self.preferred_seed is not None:
            _require_non_negative("preferred_seed", self.preferred_seed)
        if self.expected_severity and self.expected_severity not in {"none", "low", "medium", "high"}:
            raise ValueError("expected_severity must be none, low, medium, or high")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnnotationCase":
        case = cls(**data)
        case.validate()
        return case

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class AnnotationSet:
    name: str
    purpose: str
    cases: List[AnnotationCase]

    def validate(self) -> None:
        _require_non_empty("name", self.name)
        _require_non_empty("purpose", self.purpose)
        if not self.cases:
            raise ValueError("annotation set must include at least one case")
        for case in self.cases:
            case.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AnnotationSet":
        annotation_set = cls(
            name=data["name"],
            purpose=data["purpose"],
            cases=[AnnotationCase.from_dict(item) for item in data.get("cases", [])],
        )
        annotation_set.validate()
        return annotation_set

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "name": self.name,
            "purpose": self.purpose,
            "cases": [case.to_dict() for case in self.cases],
        }


@dataclass
class ExperimentManifest:
    name: str
    purpose: str
    prompt_pack_version: str
    resource_profile: str
    scenarios: List[str]
    context_systems: List[str]
    detectors: List[str]
    policies: List[str]
    agent_backends: List[str] = field(default_factory=lambda: ["scripted_local"])
    notes: List[str] = field(default_factory=list)
    manifest_stage: str = "development"

    def validate(self) -> None:
        _require_non_empty("name", self.name)
        _require_non_empty("purpose", self.purpose)
        _require_non_empty("prompt_pack_version", self.prompt_pack_version)
        _require_non_empty("resource_profile", self.resource_profile)
        _require_non_empty("manifest_stage", self.manifest_stage)
        if not self.scenarios:
            raise ValueError("experiment manifest must include at least one scenario")
        if not self.context_systems:
            raise ValueError("experiment manifest must include at least one context system")
        if not self.detectors:
            raise ValueError("experiment manifest must include at least one detector")
        if not self.policies:
            raise ValueError("experiment manifest must include at least one policy")
        if not self.agent_backends:
            raise ValueError("experiment manifest must include at least one agent backend")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentManifest":
        manifest = cls(
            name=data["name"],
            purpose=data["purpose"],
            prompt_pack_version=data["prompt_pack_version"],
            resource_profile=data["resource_profile"],
            scenarios=data.get("scenarios", []),
            context_systems=data.get("context_systems", []),
            detectors=data.get("detectors", []),
            policies=data.get("policies", []),
            agent_backends=data.get("agent_backends", ["scripted_local"]),
            notes=data.get("notes", []),
            manifest_stage=data.get("manifest_stage", "development"),
        )
        manifest.validate()
        return manifest

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class ScenarioSpec:
    scenario_id: str
    title: str
    family: str
    split: str
    prompt_pack_version: str
    resource_profile: str
    budget_ceiling: BudgetCeiling
    intent_contract: IntentContract
    corpus: List[Dict[str, Any]]
    events: List[ScenarioEvent]
    gold_checkpoints: List[GoldCheckpoint]
    gold_outcome: Dict[str, Any]
    tags: List[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty("scenario_id", self.scenario_id)
        _require_non_empty("title", self.title)
        _require_non_empty("family", self.family)
        _require_non_empty("split", self.split)
        _require_non_empty("prompt_pack_version", self.prompt_pack_version)
        _require_non_empty("resource_profile", self.resource_profile)
        self.budget_ceiling.validate()
        self.intent_contract.validate()
        if not self.events:
            raise ValueError("scenario must contain at least one event")
        for event in self.events:
            event.validate()
        for checkpoint in self.gold_checkpoints:
            checkpoint.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioSpec":
        spec = cls(
            scenario_id=data["scenario_id"],
            title=data["title"],
            family=data["family"],
            split=data["split"],
            prompt_pack_version=data["prompt_pack_version"],
            resource_profile=data["resource_profile"],
            budget_ceiling=BudgetCeiling.from_dict(data["budget_ceiling"]),
            intent_contract=IntentContract.from_dict(data["intent_contract"]),
            corpus=data.get("corpus", []),
            events=[ScenarioEvent.from_dict(item) for item in data.get("events", [])],
            gold_checkpoints=[GoldCheckpoint.from_dict(item) for item in data.get("gold_checkpoints", [])],
            gold_outcome=data.get("gold_outcome", {}),
            tags=data.get("tags", []),
        )
        spec.validate()
        return spec

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "family": self.family,
            "split": self.split,
            "prompt_pack_version": self.prompt_pack_version,
            "resource_profile": self.resource_profile,
            "budget_ceiling": self.budget_ceiling.to_dict(),
            "intent_contract": self.intent_contract.to_dict(),
            "corpus": list(self.corpus),
            "events": [event.to_dict() for event in self.events],
            "gold_checkpoints": [checkpoint.to_dict() for checkpoint in self.gold_checkpoints],
            "gold_outcome": dict(self.gold_outcome),
            "tags": list(self.tags),
        }


@dataclass
class DriftAssessment:
    overall_score: float
    label_scores: Dict[str, float]
    severity: str
    reason_codes: List[str]
    recommended_action: str
    detector_version: str

    def validate(self) -> None:
        if not 0.0 <= self.overall_score <= 1.0:
            raise ValueError("overall_score must be between 0 and 1")
        _require_non_empty("severity", self.severity)
        _require_non_empty("recommended_action", self.recommended_action)
        _require_non_empty("detector_version", self.detector_version)
        for label, score in self.label_scores.items():
            _require_non_empty("label", label)
            if not 0.0 <= score <= 1.0:
                raise ValueError("label score must be between 0 and 1")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DriftAssessment":
        assessment = cls(**data)
        assessment.validate()
        return assessment

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class InterventionAction:
    action_type: str
    applied: bool
    reason: str
    target_checkpoint_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _require_non_empty("action_type", self.action_type)
        _require_non_empty("reason", self.reason)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionAction":
        action = cls(**data)
        action.validate()
        return action

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass
class CheckpointState:
    checkpoint_id: str
    step_id: str
    after_event_id: str
    memory_state: MemoryState
    visible_state: VisibleState

    def validate(self) -> None:
        _require_non_empty("checkpoint_id", self.checkpoint_id)
        _require_non_empty("step_id", self.step_id)
        _require_non_empty("after_event_id", self.after_event_id)
        self.memory_state.ledger.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointState":
        checkpoint = cls(
            checkpoint_id=data["checkpoint_id"],
            step_id=data["step_id"],
            after_event_id=data["after_event_id"],
            memory_state=MemoryState.from_dict(data["memory_state"]),
            visible_state=VisibleState.from_dict(data["visible_state"]),
        )
        checkpoint.validate()
        return checkpoint

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "checkpoint_id": self.checkpoint_id,
            "step_id": self.step_id,
            "after_event_id": self.after_event_id,
            "memory_state": self.memory_state.to_dict(),
            "visible_state": self.visible_state.to_dict(),
        }


@dataclass
class StepRecord:
    step_id: str
    index: int
    event_id: str
    kind: str
    content: str
    chosen_option_id: Optional[str]
    correct_option_id: Optional[str]
    chosen_drift_label: Optional[str]
    visible_state: VisibleState
    drift_assessment: DriftAssessment
    intervention: InterventionAction
    memory_state: MemoryState
    agent_backend: str = "scripted_local"
    agent_metadata: Dict[str, Any] = field(default_factory=dict)
    reason_codes: List[str] = field(default_factory=list)

    def validate(self) -> None:
        _require_non_empty("step_id", self.step_id)
        _require_non_empty("event_id", self.event_id)
        _require_non_empty("kind", self.kind)
        _require_non_empty("agent_backend", self.agent_backend)
        self.drift_assessment.validate()
        self.intervention.validate()
        self.memory_state.ledger.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepRecord":
        record = cls(
            step_id=data["step_id"],
            index=data["index"],
            event_id=data["event_id"],
            kind=data["kind"],
            content=data["content"],
            chosen_option_id=data.get("chosen_option_id"),
            correct_option_id=data.get("correct_option_id"),
            chosen_drift_label=data.get("chosen_drift_label"),
            visible_state=VisibleState.from_dict(data["visible_state"]),
            drift_assessment=DriftAssessment.from_dict(data["drift_assessment"]),
            intervention=InterventionAction.from_dict(data["intervention"]),
            memory_state=MemoryState.from_dict(data["memory_state"]),
            agent_backend=data.get("agent_backend", "scripted_local"),
            agent_metadata=data.get("agent_metadata", {}),
            reason_codes=data.get("reason_codes", []),
        )
        record.validate()
        return record

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return {
            "step_id": self.step_id,
            "index": self.index,
            "event_id": self.event_id,
            "kind": self.kind,
            "content": self.content,
            "chosen_option_id": self.chosen_option_id,
            "correct_option_id": self.correct_option_id,
            "chosen_drift_label": self.chosen_drift_label,
            "visible_state": self.visible_state.to_dict(),
            "drift_assessment": self.drift_assessment.to_dict(),
            "intervention": self.intervention.to_dict(),
            "memory_state": self.memory_state.to_dict(),
            "agent_backend": self.agent_backend,
            "agent_metadata": dict(self.agent_metadata),
            "reason_codes": list(self.reason_codes),
        }


@dataclass
class EpisodeResult:
    scenario_id: str
    context_system: str
    policy: str
    detector: str
    seed: int
    success: bool
    score: float
    first_drift_step: Optional[str]
    metrics: Dict[str, Any]
    trace_path: str
    agent_backend: str = "scripted_local"
    prompt_pack_version: str = ""
    resource_profile: str = ""
    backend_metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        _require_non_empty("scenario_id", self.scenario_id)
        _require_non_empty("context_system", self.context_system)
        _require_non_empty("policy", self.policy)
        _require_non_empty("detector", self.detector)
        _require_non_empty("agent_backend", self.agent_backend)
        _require_non_negative("seed", self.seed)
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodeResult":
        result = cls(
            scenario_id=data["scenario_id"],
            context_system=data["context_system"],
            policy=data["policy"],
            detector=data["detector"],
            seed=data["seed"],
            success=data["success"],
            score=data["score"],
            first_drift_step=data.get("first_drift_step"),
            metrics=data.get("metrics", {}),
            trace_path=data.get("trace_path", ""),
            agent_backend=data.get("agent_backend", "scripted_local"),
            prompt_pack_version=data.get("prompt_pack_version", ""),
            resource_profile=data.get("resource_profile", ""),
            backend_metadata=data.get("backend_metadata", {}),
        )
        result.validate()
        return result

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return asdict(self)
