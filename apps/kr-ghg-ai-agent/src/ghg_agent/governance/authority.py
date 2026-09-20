"""GovernanceAuthorityContext — Runtime 시점 권한 바인딩 (Governance Runtime Binding).

단순 경로/URL 외부화가 아니다. Runtime 에 다음 5개 Authority 를 바인딩하고,
이로부터 파생되는 governance 플래그를 파이프라인 전 단계에서 강제한다.

- ReferenceAuthority     : 권위 참조 모델(FAL50 registry)의 승인 상태
- CandidateSetAuthority  : 매핑 후보 생성 파이프라인(결정론+Skill)의 승인 상태
- RequirednessAuthority  : 필수성 프로파일(어떤 필드가 mandatory 인지)의 승인 상태
- AuthoringAuthority     : 실제 정규화/authoring(권위 산출물 생성)의 승인 상태
- DeliveryAuthority      : 실제 delivery(KR GEARs 제출)의 승인 상태

파생 플래그 (강제 대상):
- candidate_mapping_eligible      = reference.approved and candidate_set.approved
- requiredness_profile_approved   = requiredness.approved
- actual_normalization_eligible   = authoring.approved
- executable_mapping_eligible     = candidate_mapping_eligible
                                    and requiredness_profile_approved
                                    and actual_normalization_eligible
- kr_gears_actual_delivery_allowed = delivery.approved and executable_mapping_eligible

경로/URL 바인딩(RuntimeBinding)은 이 context 의 하위 기능이다.

현재 PoC 상태의 강제값(지시 준수):
  candidate_mapping_eligible=true, requiredness_profile_approved=false,
  executable_mapping_eligible=false, actual_normalization_eligible=false,
  kr_gears_actual_delivery_allowed=false
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AuthorityStatus(StrEnum):
    BOUND = "BOUND"            # 바인딩 + 승인 (authoritative)
    PROVISIONAL = "PROVISIONAL"  # 존재하나 미승인 (권위 아님)
    UNBOUND = "UNBOUND"       # 미바인딩


class AuthorityKind(StrEnum):
    REFERENCE = "ReferenceAuthority"
    CANDIDATE_SET = "CandidateSetAuthority"
    REQUIREDNESS = "RequirednessAuthority"
    AUTHORING = "AuthoringAuthority"
    DELIVERY = "DeliveryAuthority"


class AuthorityBinding(_M):
    kind: AuthorityKind
    status: AuthorityStatus
    identifier: str | None = None  # 예: "FAL50", validator 버전, 계약 id
    detail: str | None = None

    @property
    def approved(self) -> bool:
        return self.status == AuthorityStatus.BOUND

    @property
    def present(self) -> bool:
        return self.status in (AuthorityStatus.BOUND, AuthorityStatus.PROVISIONAL)


class RuntimeBinding(_M):
    """경로/URL 런타임 바인딩 — GovernanceAuthorityContext 의 하위 기능."""

    imo_mapping_skill_path: str
    registry_db_path: str
    code_lists_path: str
    kr_gears_delivery_mode: str
    kr_gears_api_url: str | None = None


class GovernanceAuthorityContext(_M):
    reference: AuthorityBinding
    candidate_set: AuthorityBinding
    requiredness: AuthorityBinding
    authoring: AuthorityBinding
    delivery: AuthorityBinding
    runtime_binding: RuntimeBinding
    candidate_inventory: dict | None = None  # 승인 후보 집합 메타데이터 (F-STEP7-2)

    @property
    def candidate_scope_enforcement(self) -> bool:
        """승인 후보 집합이 BOUND 되어 scope 강제가 활성인지."""
        return self.candidate_set.approved

    # --- 파생 강제 플래그 ---

    @property
    def candidate_mapping_eligible(self) -> bool:
        return self.reference.approved and self.candidate_set.approved

    @property
    def requiredness_profile_approved(self) -> bool:
        return self.requiredness.approved

    @property
    def actual_normalization_eligible(self) -> bool:
        return self.authoring.approved

    @property
    def executable_mapping_eligible(self) -> bool:
        return (
            self.candidate_mapping_eligible
            and self.requiredness_profile_approved
            and self.actual_normalization_eligible
        )

    @property
    def kr_gears_actual_delivery_allowed(self) -> bool:
        return self.delivery.approved and self.executable_mapping_eligible

    def flags(self) -> dict[str, bool]:
        return {
            "candidate_mapping_eligible": self.candidate_mapping_eligible,
            "requiredness_profile_approved": self.requiredness_profile_approved,
            "executable_mapping_eligible": self.executable_mapping_eligible,
            "actual_normalization_eligible": self.actual_normalization_eligible,
            "kr_gears_actual_delivery_allowed": self.kr_gears_actual_delivery_allowed,
        }

    def snapshot(self) -> dict:
        return {
            "authorities": {
                b.kind.value: {"status": b.status.value, "identifier": b.identifier,
                               "detail": b.detail, "approved": b.approved}
                for b in (self.reference, self.candidate_set, self.requiredness,
                          self.authoring, self.delivery)
            },
            "runtime_binding": self.runtime_binding.model_dump(mode="json"),
            "candidate_inventory": self.candidate_inventory,
            "candidate_scope_enforcement": self.candidate_scope_enforcement,
            "enforced_flags": self.flags(),
        }


def build_context(
    settings,
    *,
    reference_ready: bool,
    candidate_set_ready: bool,
    reference_version: str = "FAL50",
    validator_version: str | None = None,
    candidate_inventory: object | None = None,
) -> GovernanceAuthorityContext:
    """현재 PoC 상태의 governance context 를 구성한다.

    - reference/candidate_set: 실환경 준비 여부로 BOUND/UNBOUND (준비되면 승인).
    - requiredness: PROVISIONAL — 필수성 프로파일(P-REQ-1)은 PoC 정책이며 미승인.
    - authoring: PROVISIONAL — 실제 authoring/정규화 권한 미승인(KR GEARs authoring
      계약 미확인, k-mds normalization authorization 미부여).
    - delivery: UNBOUND — KR GEARs 실제 delivery 계약 미확인.
    """
    return GovernanceAuthorityContext(
        reference=AuthorityBinding(
            kind=AuthorityKind.REFERENCE,
            status=AuthorityStatus.BOUND if reference_ready else AuthorityStatus.UNBOUND,
            identifier=reference_version,
            detail="IMO Compendium FAL50 registry snapshot",
        ),
        candidate_set=AuthorityBinding(
            kind=AuthorityKind.CANDIDATE_SET,
            # F-STEP7-2: 승인 후보 집합(inventory)이 BOUND(파일 존재 + hash 일치)여야 승인.
            # inventory 부재/hash 오류 시 UNBOUND → candidate_mapping_eligible=false (fail-closed).
            status=AuthorityStatus.BOUND
            if (candidate_set_ready and _inventory_bound(candidate_inventory))
            else AuthorityStatus.UNBOUND,
            identifier=_inventory_id(candidate_inventory, validator_version),
            detail=_inventory_detail(candidate_inventory),
        ),
        requiredness=AuthorityBinding(
            kind=AuthorityKind.REQUIREDNESS,
            status=AuthorityStatus.PROVISIONAL,
            identifier="P-REQ-1",
            detail="필수성 프로파일 미승인 — requiredness_profile_approved=false 강제",
        ),
        authoring=AuthorityBinding(
            kind=AuthorityKind.AUTHORING,
            status=AuthorityStatus.PROVISIONAL,
            identifier=None,
            detail="실제 authoring/정규화 권한 미승인 — actual_normalization_eligible=false 강제",
        ),
        delivery=AuthorityBinding(
            kind=AuthorityKind.DELIVERY,
            status=AuthorityStatus.UNBOUND,
            identifier=None,
            detail="KR GEARs 실제 delivery 계약 미확인 — kr_gears_actual_delivery_allowed=false 강제",
        ),
        runtime_binding=RuntimeBinding(
            imo_mapping_skill_path=str(settings.imo_mapping_skill_path),
            registry_db_path=str(settings.registry_db_path),
            code_lists_path=str(settings.code_lists_path),
            kr_gears_delivery_mode=settings.kr_gears_delivery_mode,
            kr_gears_api_url=settings.kr_gears_api_url or None,
        ),
        candidate_inventory=(
            candidate_inventory.metadata()  # type: ignore[attr-defined]
            if candidate_inventory is not None else None
        ),
    )


def _inventory_bound(inv: object | None) -> bool:
    return bool(getattr(inv, "bound", False))


def _inventory_id(inv: object | None, fallback: str | None) -> str | None:
    cid = getattr(inv, "candidate_set_id", None)
    return cid or fallback


def _inventory_detail(inv: object | None) -> str:
    if inv is None:
        return "승인 후보 집합 미주입 — UNBOUND(fail-closed)"
    status = getattr(inv, "load_status", "UNBOUND")
    count = getattr(inv, "element_count", 0)
    ver = getattr(inv, "version", "")
    return f"KR GHG candidate inventory {ver} ({count} elements) load_status={status}"
