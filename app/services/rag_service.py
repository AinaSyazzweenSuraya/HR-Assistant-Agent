"""Retrieval + prompt building + answer validation + citations."""
import re

from app.services import llm_service, retrieval_service

NOT_FOUND = ("I could not find this in the company policies. "
             "Please contact HR directly so they can help you.")

SYSTEM_PROMPT = """You are the company HR policy assistant. Staff ask you about leave, claims, allowances and other company policies.

Rules:
1. Answer ONLY from the numbered policy excerpts provided. Never use outside knowledge.
2. Never guess amounts, days, dates, limits or eligibility. Quote them exactly as written.
3. After each fact, cite the excerpt number like [1] or [2].
4. If the excerpts do not contain the answer, reply exactly: "I could not find this in the company policies."
5. If the policy differs by employment type or grade, state which one applies to this employee, or list the differences if unclear.
6. Be concise and friendly. Use short bullet points for steps or limits.

Employee profile: {profile}"""

CITE_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


def _profile(user):
    grade = f", grade {user['grade']}" if user.get("grade") else ""
    return f"{user['employment_type']} staff{grade}"


def _snippet(text, n=220):
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n].rstrip() + "..."


def answer(question, user, history=None):
    history = [h for h in (history or [])
               if h.get("role") in ("user", "assistant") and isinstance(h.get("content"), str)]

    # Follow-ups like "what about contract staff?" need the previous question for retrieval.
    prev_user = next((h["content"] for h in reversed(history) if h["role"] == "user"), "")
    chunks = retrieval_service.search(f"{prev_user} {question}".strip() if prev_user else question, user)
    if not chunks:
        return {"answer": NOT_FOUND, "sources": [], "answered": False}

    context = "\n\n".join(
        f"[{i}] {c['doc_name']} (v{c['version']}), {c['section'] or 'General'}, page {c['page']}\n{c['text']}"
        for i, c in enumerate(chunks, 1))
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(profile=_profile(user))}]
    messages += [{"role": h["role"], "content": h["content"][:1500]} for h in history[-6:]]
    messages.append({"role": "user", "content": f"POLICY EXCERPTS:\n{context}\n\nQUESTION: {question}"})

    text = llm_service.chat(messages)

    if "could not find this in the company policies" in text.lower():
        return {"answer": NOT_FOUND, "sources": [], "answered": False}

    cited = {int(n) for m in CITE_RE.findall(text) for n in re.split(r"\s*,\s*", m)}
    cited = {n for n in cited if 1 <= n <= len(chunks)}
    verified = bool(cited)
    if not verified:
        cited = {1, 2} & set(range(1, len(chunks) + 1))
        text += "\n\n(I could not link this answer to a specific clause. Please confirm with HR.)"

    sources = [{
        "id": n, "document": chunks[n - 1]["doc_name"], "version": chunks[n - 1]["version"],
        "category": chunks[n - 1]["category"], "section": chunks[n - 1]["section"],
        "page": chunks[n - 1]["page"], "snippet": _snippet(chunks[n - 1]["text"]),
    } for n in sorted(cited)]
    return {"answer": text, "sources": sources, "answered": True, "verified": verified}
