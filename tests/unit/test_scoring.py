from __future__ import annotations

from datetime import UTC, datetime

import pytest
from src.job_finder.domain.candidate import (
    CandidateFact,
    ClaimType,
    FactProvenance,
    SourceKind,
    SourceReference,
)
from src.job_finder.domain.errors import ScoringPolicyValidationError
from src.job_finder.domain.ids import CandidateFactId, CandidateSourceId
from src.job_finder.domain.scoring import (
    CriterionEvaluation,
    CriterionEvidenceStatus,
    score_criteria,
)
from src.job_finder.domain.scoring_policy import (
    CURRENT_SCORING_POLICY,
    ScoringFactor,
    ScoringPolicy,
    ScoringPolicyVersion,
)


def test_score_criteria_uses_fixed_weights_and_half_up_rounding() -> None:
    python_fact = _candidate_fact(
        fact_id="fact-python",
        name="skill",
        value="Python",
        locator="experience[0].skills[0]",
        excerpt="Built internal automation in Python.",
    )
    sql_fact = _candidate_fact(
        fact_id="fact-sql",
        name="tool",
        value="SQL",
        locator="experience[0].tools[0]",
        excerpt="Used SQL to support reporting.",
    )
    senior_fact = _candidate_fact(
        fact_id="fact-seniority",
        name="seniority",
        value="Senior",
        locator="summary",
        excerpt="Senior backend engineer.",
    )
    fintech_fact = _candidate_fact(
        fact_id="fact-domain",
        name="domain",
        value="Fintech",
        locator="experience[1].domain",
        excerpt="Delivered backend systems for fintech products.",
    )
    english_fact = _candidate_fact(
        fact_id="fact-language",
        name="language",
        value="English",
        locator="languages[0]",
        excerpt="English — professional working proficiency.",
    )

    result = score_criteria(
        criteria=(
            CriterionEvaluation(
                factor=ScoringFactor.ROLE_ALIGNMENT,
                criterion_id="role-backend",
                description="Backend engineering role alignment",
                source_fields=("title", "summary"),
                job_evidence_references=("job:title", "job:summary"),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(senior_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.SKILLS_TOOLS,
                criterion_id="skill-python",
                description="Explicit Python requirement",
                source_fields=("requirements.skills",),
                job_evidence_references=("job:requirements.skills[0]",),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(python_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.SKILLS_TOOLS,
                criterion_id="tool-sql",
                description="Explicit SQL requirement",
                source_fields=("requirements.tools",),
                job_evidence_references=("job:requirements.tools[0]",),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(sql_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.SKILLS_TOOLS,
                criterion_id="tool-airflow",
                description="Explicit Airflow requirement",
                source_fields=("requirements.tools",),
                job_evidence_references=("job:requirements.tools[1]",),
                evidence_status=CriterionEvidenceStatus.MISSING,
                matched_facts=(),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.EXPERIENCE_SENIORITY,
                criterion_id="experience-years",
                description="Demonstrated backend experience",
                source_fields=("requirements.experience",),
                job_evidence_references=("job:requirements.experience",),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(senior_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.EXPERIENCE_SENIORITY,
                criterion_id="experience-scope",
                description="Demonstrated delivery scope",
                source_fields=("responsibilities",),
                job_evidence_references=("job:responsibilities[0]",),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(senior_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.DOMAIN_RELEVANCE,
                criterion_id="domain-fintech",
                description="Fintech domain relevance",
                source_fields=("industry",),
                job_evidence_references=("job:industry",),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(fintech_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.PREFERRED_QUALIFICATIONS,
                criterion_id="language-english",
                description="Preferred English fluency",
                source_fields=("preferred.languages",),
                job_evidence_references=("job:preferred.languages[0]",),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(english_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.PREFERRED_QUALIFICATIONS,
                criterion_id="cert-aws",
                description="Preferred AWS certification",
                source_fields=("preferred.certifications",),
                job_evidence_references=("job:preferred.certifications[0]",),
                evidence_status=CriterionEvidenceStatus.MISSING,
                matched_facts=(),
            ),
        ),
    )

    assert result.score == 88
    assert result.policy_version == CURRENT_SCORING_POLICY.version

    role_explanation = result.factor_explanations[0]
    assert role_explanation.factor is ScoringFactor.ROLE_ALIGNMENT
    assert role_explanation.weight == 30
    assert role_explanation.applicable_criteria_count == 1
    assert role_explanation.supported_criteria_count == 1
    assert role_explanation.is_applicable is True

    skills_explanation = result.factor_explanations[1]
    assert skills_explanation.factor is ScoringFactor.SKILLS_TOOLS
    assert skills_explanation.weight == 30
    assert skills_explanation.applicable_criteria_count == 3
    assert skills_explanation.supported_criteria_count == 2
    assert skills_explanation.criteria[2].criterion_score == 0
    assert (
        skills_explanation.criteria[2].evidence_status
        is CriterionEvidenceStatus.MISSING
    )

    preferred_explanation = result.factor_explanations[4]
    assert preferred_explanation.factor is ScoringFactor.PREFERRED_QUALIFICATIONS
    assert preferred_explanation.criteria[0].evidence_references == (
        "job:preferred.languages[0]",
        "cv-2026-07#languages[0]",
    )
    assert preferred_explanation.source_fields == (
        "preferred.certifications",
        "preferred.languages",
    )


def test_score_criteria_uses_applicable_denominator_and_zero_for_ambiguous_evidence(
) -> None:
    python_fact = _candidate_fact(
        fact_id="fact-python",
        name="skill",
        value="Python",
        locator="experience[0].skills[0]",
        excerpt="Built internal automation in Python.",
    )

    result = score_criteria(
        criteria=(
            CriterionEvaluation(
                factor=ScoringFactor.ROLE_ALIGNMENT,
                criterion_id="role-backend",
                description="Backend engineering role alignment",
                source_fields=("title",),
                job_evidence_references=("job:title",),
                evidence_status=CriterionEvidenceStatus.AMBIGUOUS,
                matched_facts=(python_fact,),
            ),
            CriterionEvaluation(
                factor=ScoringFactor.SKILLS_TOOLS,
                criterion_id="skill-python",
                description="Explicit Python requirement",
                source_fields=("requirements.skills",),
                job_evidence_references=("job:requirements.skills[0]",),
                evidence_status=CriterionEvidenceStatus.SUPPORTED,
                matched_facts=(python_fact,),
            ),
        ),
    )

    assert result.score == 30

    role_explanation = result.factor_explanations[0]
    assert role_explanation.applicable_criteria_count == 1
    assert role_explanation.supported_criteria_count == 0
    assert role_explanation.criteria[0].criterion_score == 0
    assert (
        role_explanation.criteria[0].evidence_status
        is CriterionEvidenceStatus.AMBIGUOUS
    )

    domain_explanation = result.factor_explanations[3]
    assert domain_explanation.applicable_criteria_count == 0
    assert domain_explanation.supported_criteria_count == 0
    assert domain_explanation.is_applicable is False


def test_scoring_policy_rejects_in_place_weight_change_without_new_version() -> None:
    with pytest.raises(ScoringPolicyValidationError, match="must change version"):
        _ = ScoringPolicy(
            version=ScoringPolicyVersion(CURRENT_SCORING_POLICY.version.value),
            factor_weights=(
                (ScoringFactor.ROLE_ALIGNMENT, 35),
                (ScoringFactor.SKILLS_TOOLS, 25),
                (ScoringFactor.EXPERIENCE_SENIORITY, 25),
                (ScoringFactor.DOMAIN_RELEVANCE, 10),
                (ScoringFactor.PREFERRED_QUALIFICATIONS, 5),
            ),
        )


def _candidate_fact(
    *,
    fact_id: str,
    name: str,
    value: str,
    locator: str,
    excerpt: str,
) -> CandidateFact:
    return CandidateFact(
        fact_id=CandidateFactId(fact_id),
        name=name,
        value=value,
        claim_type=ClaimType.VERBATIM,
        provenance=FactProvenance(
            source=SourceReference(
                source_id=CandidateSourceId("cv-2026-07"),
                kind=SourceKind.CV,
                locator=locator,
                captured_at=datetime(2026, 7, 22, 9, 0, tzinfo=UTC),
            ),
            source_claim_type=ClaimType.VERBATIM,
            derived_claim_type=ClaimType.VERBATIM,
            source_excerpt=excerpt,
        ),
    )
