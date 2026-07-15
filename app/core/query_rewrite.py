from app.services.gemini_client import generate_text

REWRITE_PROMPT_TEMPLATE = """You are an assistant for a customer support bot.
Rewrite the short customer message below into a clear, complete search query / question that can be matched against an FAQ knowledge base.
Write the question from the customer's perspective (e.g. use "your" or "you"). Do NOT add the brand name "SafeX Solutions" or "SafeX" unless the user explicitly mentioned it.
Keep it under 15 words. Only output the rewritten question, nothing else.

Message: "{query}"
Rewritten question:"""


def rewrite_query(query: str) -> str:
    """
    Expands short/ambiguous queries into fuller search queries.
    Skips rewriting for already-clear, longer questions to save latency/cost.
    """
    if len(query.split()) >= 6:
        return query  # already a full question, skip the extra LLM call

    try:
        prompt = REWRITE_PROMPT_TEMPLATE.format(query=query)
        rewritten = generate_text(prompt, temperature=0.2)
        return rewritten if rewritten else query
    except Exception:
        # Never let a query-rewrite failure block the retrieval pipeline
        return query
