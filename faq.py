from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, List, Tuple
from difflib import SequenceMatcher

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'data', 'faq.json')

STOPWORDS = {
	"what","should","i","do","if","is","am","are","the","a","an","to","for","with","my","of","in","on","at","and","or","be","can","able","someone","somebody","friend","frnd","they","who","dont","don't","know","me","im"
}

# Intent keywords to boost domain-relevant matches
INTENT_KEYWORDS = {
	"fire": ["fire", "smoke", "burn", "burning", "extinguisher"],
	"cpr": ["cpr", "cardiac", "no pulse", "not breathing", "cant breathe", "can't breathe", "cannot breathe", "stopped breathing", "unresponsive", "aed", "defibrillator", "rescue breaths"],
	"bleeding": ["bleeding", "hemorrhage", "tourniquet", "blood"],
	"choking": ["choke", "choking", "heimlich", "abdominal thrust"],
	"stroke": ["stroke", "fast", "face droop"],
	"asthma": ["asthma", "inhaler", "wheezing", "shortness of breath"],
	"respiratory": ["cold", "cough", "flu", "fever", "sore throat", "runny nose", "congestion", "breath", "breathing"],
	"chestpain": ["chest pain", "heart pain", "tightness chest", "pressure chest"],
	"safety": ["follow", "following", "stalk", "stalking", "unsafe", "panic", "anxious", "threat", "self defense", "self-defence", "self-defense", "harass", "harassment", "fear", "afraid"]
}

# Phrase keywords for strong boosts
PHRASE_KEYWORDS = [
	("not breathing", "cpr"),
	("can't breathe", "respiratory"),
	("cant breathe", "respiratory"),
	("cannot breathe", "respiratory"),
	("stopped breathing", "cpr"),
	("heart pain", "chestpain"),
	("chest pain", "chestpain"),
	("someone is following me", "safety"),
	("being followed", "safety"),
	("feel unsafe", "safety"),
	("panic attack", "safety"),
	("self defense", "safety"),
]


def _normalize(text: str) -> List[str]:
	words = [t for t in ''.join([c.lower() if c.isalnum() else ' ' for c in (text or '')]).split() if t]
	return [w for w in words if w not in STOPWORDS]


@lru_cache(maxsize=1)
def load_faq() -> List[Dict[str, Any]]:
	path = os.path.normpath(DATA_PATH)
	if not os.path.exists(path):
		return []
	with open(path, 'r', encoding='utf-8') as f:
		return json.load(f)


def _fuzzy(a: str, b: str) -> float:
	# Ratio in [0,1]
	return SequenceMatcher(None, (a or '').lower(), (b or '').lower()).ratio()


def _detect_intents(raw_query: str) -> List[str]:
	q = (raw_query or '').lower()
	hits: List[str] = []
	for intent, keys in INTENT_KEYWORDS.items():
		if any(k in q for k in keys):
			hits.append(intent)
	for phrase, intent in PHRASE_KEYWORDS:
		if phrase in q and intent not in hits:
			hits.append(intent)
	return hits


def _intent_bonus(intents: List[str], question: str, answer: str) -> float:
	if not intents:
		return 0.0
	text = f"{question} {answer}".lower()
	score = 0.0
	for intent in intents:
		keys = INTENT_KEYWORDS.get(intent, [])
		if any(k in text for k in keys):
			score += 1.2
	return min(score, 3.0)  # cap


def _score(q_tokens: List[str], raw_query: str, item: Dict[str, Any], intents: List[str]) -> Tuple[float, Dict[str, float]]:
	question = item.get('question', '')
	answer = item.get('answer', '')
	text = f"{question} {answer}"
	itokens = _normalize(text)
	iset = set(itokens)
	qset = set(q_tokens)
	# Jaccard
	inter = len(qset & iset)
	union = len(qset | iset) or 1
	jaccard = inter / union
	# Containment boost
	contain = (inter / (len(qset) or 1))
	# Fuzzy similarity against question text only
	fuzzy_q = _fuzzy(raw_query, question)
	# Substring bonuses (question weighted higher than answer)
	raw = raw_query.strip().lower()
	sub_q = 1.2 if (raw and raw in question.lower()) else 0.0
	sub_a = 0.8 if (raw and raw in answer.lower()) else 0.0
	# Intent bonus
	intent = _intent_bonus(intents, question, answer)
	# Composite
	score = 0.22 * jaccard + 0.18 * contain + 0.16 * fuzzy_q + 0.28 * sub_q + 0.06 * sub_a + 0.10 * intent
	components = {"jaccard": jaccard, "contain": contain, "fuzzy_q": fuzzy_q, "sub_q": sub_q, "sub_a": sub_a, "intent": intent}
	return score, components


def search_faq(query: str, limit: int = 5) -> List[Dict[str, Any]]:
	raw_query = (query or '').strip()
	q_tokens = _normalize(raw_query)
	items = load_faq()
	if not items:
		return []

	# If no tokens (very short/empty), return the top N canonical FAQs
	if not q_tokens:
		base = [{**item, 'score': 0.0} for item in items[:max(1, limit)]]
		return base

	intents = _detect_intents(raw_query)
	scored: List[Tuple[float, Dict[str, Any]]] = []
	for item in items:
		s, comps = _score(q_tokens, raw_query, item, intents)
		scored.append((s, {**item, 'score': round(s, 4), 'debug': comps}))

	scored.sort(key=lambda x: x[0], reverse=True)
	top = [itm for _, itm in scored]

	# Safeguard: prefer items where question includes key phrase from PHRASE_KEYWORDS
	for phrase, _ in PHRASE_KEYWORDS:
		if phrase in raw_query.lower():
			prefer = next((it for it in top if phrase in it.get('question','').lower()), None)
			if prefer:
				top.insert(0, prefer)
				break

	return top[:max(1, limit)]
