def ats_score(resume_text, jd_text):
    resume_words = set(resume_text.lower().split())
    jd_words = set(jd_text.lower().split())

    match = resume_words.intersection(jd_words)
    score = int((len(match) / max(len(jd_words), 1)) * 100)
    missing = list(jd_words - resume_words)

    return score, missing
