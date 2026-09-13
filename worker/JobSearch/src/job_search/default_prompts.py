DEFAULT_JOB_FILTER_PROMPT = """You are analyzing a LinkedIn job posting.

Return ONLY valid JSON with exactly these keys:
- match: boolean
- score: integer 0..100
- reason: string (1-3 sentences)
- matched_requirements: array of strings
- missing_requirements: array of strings
- red_flags: array of strings

Job text:
<<<JOB_TEXT>>>
"""

