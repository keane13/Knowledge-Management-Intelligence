import re

try:
    from guardrails import Guard
    from guardrails.hub import ToxicLanguage, PromptInjection
    import nltk
    nltk.download("punkt", quiet=True); nltk.download("punkt_tab", quiet=True)
    input_guard = Guard().use_many(
        ToxicLanguage(threshold=0.5, validation_method="sentence", target_metric="toxicity"),
        PromptInjection(threshold=0.5)
    )
except ImportError:
    input_guard = None

def validate_input(text: str) -> bool:
    if input_guard:
        try:
            return input_guard.validate(text).validation_passed
        except Exception:
            return False
    return _basic_check(text)

def _basic_check(text: str) -> bool:
    patterns = [
        r"drop\s+table", r"delete\s+from", r"truncate\s+table",
        r"insert\s+into", r"update\s+.*set",
        r"ignore\s+all\s+previous\s+instructions", r"system\s+prompt\s+bypass"
    ]
    lower = text.lower()
    return not any(re.search(p, lower) for p in patterns)

def validate_sql_read_only(sql: str) -> bool:
    if not sql: return False
    return not any(f in sql.upper() for f in
                   ["INSERT","UPDATE","DELETE","DROP","ALTER","CREATE","TRUNCATE"])
