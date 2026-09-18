"""Chặn sớm: prompt injection, yêu cầu ngoài phạm vi, thuật ngữ biết chắc ngoài bài. Không gọi LLM."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .textutil import norm

INJECTION = re.compile(
    r"bo qua (moi |cac |tat ca )?(huong dan|chi dan|quy tac)|ignore (all |the )?(previous|above|prior)|"
    r"system_override|system prompt|jailbreak|developer mode|dong vai (la )?(he thong|admin)"
)
OUT_OF_SCOPE = re.compile(r"viet (mot |1 )?(bai )?blog|diem danh|deadline|han nop|\bxp\b|lam ho|giai ho|nop bai ho|lam bai ho|dap an (cua )?quiz")
ABILITY_LABEL = re.compile(r"ban (yeu|kem|dot)|trinh do (cua ban )?thap|ban khong co kha nang|hoc kem")


@dataclass
class GuardResult:
    injection: bool
    out_of_scope: bool
    outside_term: str | None

    @property
    def blocked(self) -> bool:
        return self.injection or self.out_of_scope or bool(self.outside_term)


def check_input(text: str, selection: str, outside_terms) -> GuardResult:
    n_all = norm(f"{text} {selection}")
    n_q = norm(text)
    outside = None
    for term in outside_terms:
        if re.search(rf"(?<![a-z0-9]){re.escape(norm(term))}(?![a-z0-9])", n_q):
            outside = term
            break
    return GuardResult(injection=bool(INJECTION.search(n_all)), out_of_scope=bool(OUT_OF_SCOPE.search(n_q)), outside_term=outside)


def ability_labels(text: str) -> list[str]:
    return [m.group(0) for m in ABILITY_LABEL.finditer(norm(text))]
