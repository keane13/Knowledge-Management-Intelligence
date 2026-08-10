def hallucination_check(answer, context):
    missing = [
        sent for sent in answer.split(".")
        if sent and sent.lower() not in context.lower()
    ]
    return len(missing) == 0
