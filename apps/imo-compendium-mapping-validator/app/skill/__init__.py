"""AI Agent용 Tool/Skill 인터페이스.

- Agent는 `MappingToolkit.invoke(tool_name, arguments)`로만 엔진을 호출한다.
- 모든 입력은 Pydantic 계약으로 검증되고, 필드명·설명은 **데이터**로만
  취급된다 — 어떤 경로에서도 지시문으로 해석·실행되지 않는다 (전 파이프라인이
  결정론 코드이며 이 계층에는 LLM이 없다).
- Registry 전체 원문은 Agent에게 전달되지 않는다 — top-k 후보와 단일 record
  근거 요약만 반환한다.
"""

from app.skill.service import MappingSkillService, SkillError
from app.skill.toolkit import MappingToolkit, TOOL_NAMES

__all__ = ["MappingSkillService", "MappingToolkit", "SkillError", "TOOL_NAMES"]
