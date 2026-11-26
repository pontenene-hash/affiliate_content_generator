"""Offline routing policy. No network, publishing, or factual approval."""
from dataclasses import dataclass
from specialist_review import classify

@dataclass(frozen=True)
class Route:
    strategy: str
    categories: tuple
    max_generation_calls: int
    human_review_required: bool = True

def route(name, genre, context='', *, evidence_count=0, comparison=False, call_budget=8):
    if type(evidence_count) is not int or evidence_count < 0 or type(call_budget) is not int or call_budget < 0:
        raise ValueError('invalid budget or evidence count')
    tags=tuple(classify(name,genre,context))
    sensitive=bool(set(tags)&{'medical','nutrition','cosmetic','health_unknown','contract','food'})
    if not evidence_count or not call_budget or (sensitive and call_budget < 3) or (comparison and call_budget < 2):
        return Route('hold_for_research',tags,0)
    if sensitive:
        return Route('evidence_first_sections',tags,min(call_budget,8))
    if comparison:
        return Route('comparison_first',tags,min(call_budget,4))
    return Route('single_then_targeted_repair',tags,min(call_budget,3))
