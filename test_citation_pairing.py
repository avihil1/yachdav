#!/usr/bin/env python3
"""Guard the one deterministic part of pairing: citations.

Deciding that some message answers some question is judgement, and the proximity
heuristics get it wrong sometimes — that is expected and not what this checks.
A WhatsApp citation is different: the reply carries the quoted message's id, so the
link is recorded fact. Every such pair must anchor on the message that was actually
quoted, never on "the closest earlier question from that person" — that guess is what
made the muktzeh answer point at an unrelated blessing thread, and it silently reappears
if anyone re-orders the resolution in extract_qa.extract_qa_pairs.

Run standalone, or via extract_qa.py, which calls verify() on every rebuild.
"""
import sys

RAW_PATH = "/Users/hillelk/Documents/shut-yachdav/raw_messages.txt"

# (question fragment, answer fragment) — pairs that only exist when citations resolve by
# id. Each was absent from the site while senders were collapsed and replies were matched
# by sender; if one disappears again, the same class of bug is back.
GOLDEN = [
    ("האם מותר להרים את האגרטל", "אין בזה בעיית מוקצה"),          # 2026-09-04
    ("שופר, ישן האם צריך גניזה", "תשמישי קדושה הם חפצים"),         # 2026-08-14
    ("אדם עבר הליך רפואי", "יש להניח את  התפילין של ראש בעדינ"),   # 2026-08-18
    ("קציצות בשריות שבושלו עם מכסה חלבי", "בהחלט ניתן להגעיל"),    # 2026-09-05
]


def verify(raw_path=RAW_PATH, max_report=5):
    from rebuild_raw_section import (
        parse_messages, classify_all_messages, strip_reply_metadata, load_msg_id_timestamps)
    import extract_qa as E

    messages = parse_messages(open(raw_path, encoding="utf-8").read())
    roles = classify_all_messages(messages)
    reply_infos = []
    for _, _, text in messages:
        _, sender, msg_id = strip_reply_metadata(text)
        reply_infos.append((sender, msg_id) if sender else None)

    ts_by_msg_id = load_msg_id_timestamps()
    if not ts_by_msg_id:
        return "skipped: bridge DB unavailable, no citations to resolve"

    ts_index = {}
    for idx, (ts, _, _) in enumerate(messages):
        ts_index.setdefault(ts, idx)

    pairs = E.extract_qa_pairs(messages, roles, reply_infos)
    # A cited question can be answered across several rabbi messages, so index every
    # pair by each question line it carries.
    by_line = {}
    for p in pairs:
        for line in p["question"].split("\n"):
            key = line.strip()[:60]
            if len(key) >= 8:
                by_line.setdefault(key, []).append(p)

    checked = misanchored = 0
    failures = []
    for rabbi_idx, info in enumerate(reply_infos):
        if roles[rabbi_idx] != "הרב" or not info or not info[1]:
            continue
        target_ts = ts_by_msg_id.get(info[1])
        if target_ts is None:
            continue
        cited = ts_index.get(target_ts)
        if cited is None or cited >= rabbi_idx or roles[cited] not in ("שואל", "תגובה"):
            continue

        cited_text = E._clean_text(messages[cited][2]).strip()
        if len(cited_text) < 8 or cited_text == "[media]":
            continue
        checked += 1

        key = cited_text.split("\n")[0].strip()[:60]
        owners = by_line.get(key, [])
        answer = E._clean_text(messages[rabbi_idx][2]).strip()[:40]
        if not any(answer in p["answer"] for p in owners):
            misanchored += 1
            if len(failures) < max_report:
                failures.append(f"    cited={cited} answer={rabbi_idx} q={key[:45]!r}")

    # Not 100%, and that is a fact about the data rather than slack in the check: a
    # citation is a swipe in a chat app, so a few point at the wrong message while the
    # text answers something else entirely (a popcorn question quoted under a nusach
    # answer). Those keep their content-based pairing. What must never come back is the
    # old sender-scan resolution, which mis-anchored a third of all replies — that shows
    # up here as a collapse in the rate, not as one stray.
    rate = (checked - misanchored) / checked if checked else 1.0
    assert rate >= 0.95, (
        f"only {rate:.1%} of {checked} cited answers anchor on the message they quote "
        f"(expected >=95%); citation resolution has regressed:\n" + "\n".join(failures))

    # Golden cases: the exact pairs the sender-scan bug broke. Matched on collapsed
    # whitespace — a question is often split across lines mid-sentence.
    import re as _re
    flat = lambda s: _re.sub(r"\s+", " ", s)
    for question_snippet, answer_snippet in GOLDEN:
        question_snippet, answer_snippet = flat(question_snippet), flat(answer_snippet)
        pairs_flat = [{"question": flat(p["question"]), "answer": flat(p["answer"])} for p in pairs]
        owners = [p for p in pairs_flat if question_snippet in p["question"]]
        assert owners, f"golden question vanished from the corpus: {question_snippet!r}"
        assert any(answer_snippet in p["answer"] for p in owners), (
            f"golden pair broken: {question_snippet!r} no longer answered by {answer_snippet!r}")

    return (f"{checked} cited answers, {rate:.1%} anchored on the quoted message, "
            f"{len(GOLDEN)} golden pairs intact")


if __name__ == "__main__":
    try:
        print(verify())
    except AssertionError as e:
        print(f"CITATION CHECK FAILED: {e}", file=sys.stderr)
        sys.exit(1)
