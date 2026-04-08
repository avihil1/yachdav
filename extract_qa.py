#!/usr/bin/env python3
"""
Extract ALL Q&A pairs from raw_messages.txt using heuristic role classification.
Categorize each pair and generate complete HTML category sections.
"""
import re
import json
from rebuild_raw_section import (
    parse_messages, classify_all_messages, RABBI_SENDERS, get_sender_name
)

RAW_PATH = "/Users/hillelk/Documents/shut-yachdav/raw_messages.txt"
HTML_PATH = "/Users/hillelk/Documents/shut-yachdav/shut-yachdav-qa.html"

# Category definitions with keyword matching
CATEGORIES = [
    ("cat1", "כשרות - בשר וחלב", [
        "בשר", "חלב", "חלבי", "בשרי", "פרווה", "בן יומו", "כשרה", "מחבת",
        "סיר", "תנור בשרי", "תנור חלבי", "נטרפ", "הגעלה", "ליבון", "כלי בשרי",
        "כלי חלבי", "טרף", "נבלה", "שחיטה", "כבד", "מליחה", "דם",
    ]),
    ("cat2", "כשרות - כללי", [
        "כשרות", "כשר", "הכשר", "השגחה", "תולעים", "בדץ", "רבנות",
        "מסעדה", "אוכל", "מזון", "חומץ", "יין", "בישולי", "בישול עכו\"ם",
        "בישול גויים", "פת עכו\"ם", "חלב עכו\"ם", "גבינה", "סתם יינם",
        "תערובת", "ביטול", "שישים",
    ]),
    ("cat3", "כשרות - בדיקת חרקים ותוצרת", [
        "חרק", "תולע", "בדיקה", "עלים", "חסה", "ירק", "ירוק", "פטרוזיליה",
        "כוסברה", "שמיר", "נענע", "תבלין", "קמח", "אורז", "קטניות",
        "גרעינים", "פירות יבשים",
    ]),
    ("cat4", "כשרות - טבילת כלים", [
        "טביל", "מקוה", "מקווה", "כלי מתכת", "כלי זכוכית", "כלי חשמלי",
        "טבילת כלים", "טבילה",
    ]),
    ("cat5", "כשרות - הפרשת חלה", [
        "חלה", "הפרשת חלה", "עיסה", "קמח", "לש", "לישה", "הפרשה",
    ]),
    ("cat6", "ברכות", [
        "ברכה", "מברכ", "שהכל", "המוציא", "מזונות", "העץ", "האדמה",
        "הגפן", "ברכת", "ברכה אחרונה", "על המחיה", "בורא נפשות",
        "שהחיינו", "הטוב והמטיב", "מעין שלוש", "ברהמ\"ז", "ברכת המזון",
        "ברכה ראשונה", "שם ומלכות",
    ]),
    ("cat7", "שבת", [
        "שבת", "מוצ\"ש", "מוצאי שבת", "ערב שבת", "נרות שבת",
        "קידוש", "הבדלה", "מוקצה", "מלאכה", "בורר", "בישול בשבת",
        "חימום", "פלטה", "פלאטה", "שהיה", "חזרה", "הטמנה",
        "אמירה לגוי", "מנוחת שבת", "עירוב", "טלטול", "כתיבה",
        "הדלקת נרות", "סעודה שלישית", "מלווה מלכה",
        "שבת שלום", "ליל שבת", "יום שבת", "כבוד שבת",
    ]),
    ("cat8", "תפילה", [
        "תפיל", "מנחה", "ערבית", "שחרית", "מוסף", "מנין", "מניין",
        "חזרת הש\"ץ", "שמונה עשרה", "עמידה", "קריאת שמע",
        "פסוקי דזמרה", "ברכות השחר", "תחנון", "הלל", "קדיש",
        "עלייה לתורה", "קריאת התורה", "ציצית", "תפילין", "כיפה",
        "סידור", "נוסח", "ספירת העומר", "ברכת כהנים",
        "מעריב", "ותיקין",
    ]),
    ("cat9", "פסח", [
        "פסח", "מצה", "חמץ", "הגדה", "סדר", "אפיקומן",
        "מרור", "חרוסת", "ארבע כוסות", "קערת", "בדיקת חמץ",
        "ביעור חמץ", "מכירת חמץ", "כשר לפסח", "קטניות",
        "מצות", "שמורה",
    ]),
    ("cat10", "חנוכה", [
        "חנוכ", "נר חנוכה", "חנוכיה", "מנורה", "סביבון",
        "סופגניה", "לביבה", "שמן זית", "הדלקת נרות חנוכה",
        "על הניסים", "מזוזת",
    ]),
    ("cat11", "פורים", [
        "פורים", "מגילה", "משלוח מנות", "מתנות לאביונים",
        "סעודת פורים", "תחפושת", "עד דלא ידע",
    ]),
    ("cat12", "מזוזה", [
        "מזוזה", "מזוזות", "קלף", "סופר סת\"ם",
    ]),
    ("cat13", "צדקה ומעשרות", [
        "צדקה", "מעשר", "תרומה", "תרומות", "מעשרות",
        "עני", "חומש", "מתנות לאביונים", "הפרשת תרומות",
    ]),
    ("cat14", "לשון הרע ורכילות", [
        "לשון הרע", "רכילות", "דיבור", "שמירת הלשון", "חפץ חיים",
    ]),
    ("cat15", "הלכות שונות", []),  # Fallback
]

# Additional categories for topics that appear frequently in the full history
EXTRA_CATEGORIES = [
    ("cat16", "צום ותענית", [
        "צום", "תענית", "צם", "תשעה באב", "י\"ז בתמוז", "עשרה בטבת",
        "צום גדליה", "תענית אסתר", "סליחות",
    ]),
    ("cat17", "נידה וטהרת המשפחה", [
        "נידה", "טהרה", "מקוה", "מקווה", "טהרת המשפחה", "הפסק טהרה",
        "וסת", "בדיקה", "ליבון", "כתם",
    ]),
    ("cat18", "אבלות וזכרון", [
        "אבל", "שבעה", "שלושים", "יארצייט", "קדיש", "הזכרה",
        "מצבה", "אנינות", "קריעה", "לוויה", "הספד",
        "נפטר", "פטירה", "זכר",
    ]),
    ("cat19", "ראש השנה ויום כיפור", [
        "ראש השנה", "יום כיפור", "שופר", "תשובה", "סליחות",
        "כפרות", "תשליך", "מחזור", "עשרת ימי תשובה",
        "נעילה", "כל נדרי",
    ]),
    ("cat20", "סוכות ושמחת תורה", [
        "סוכה", "סוכות", "לולב", "אתרוג", "ארבעת המינים",
        "הושענא רבה", "שמיני עצרת", "שמחת תורה",
        "ישיבה בסוכה", "סכך",
    ]),
    ("cat21", "כיבוד הורים ובין אדם לחברו", [
        "כיבוד אב", "כיבוד הורים", "כיבוד אם", "בין אדם לחברו",
        "שכנים", "גניבת דעת", "הלוואה", "חוב", "נזק",
        "השבת אבידה", "גזל",
    ]),
    ("cat22", "נישואין ומשפחה", [
        "חתונה", "נישואין", "חופה", "קידושין", "כתובה",
        "שבע ברכות", "שידוך", "גירושין", "גט",
        "להתחתן",
    ]),
]

ALL_CATEGORIES = CATEGORIES[:-1] + EXTRA_CATEGORIES + [CATEGORIES[-1]]  # הלכות שונות last


def categorize_qa(question_text, answer_text):
    """Determine the best category for a Q&A pair."""
    combined = question_text + " " + answer_text
    combined_lower = combined.lower()

    best_cat = None
    best_score = 0

    for cat_id, cat_name, keywords in ALL_CATEGORIES:
        if not keywords:
            continue
        score = 0
        for kw in keywords:
            if kw in combined:
                score += 1
                # Bonus for keyword in the question (more relevant)
                if kw in question_text:
                    score += 0.5
        if score > best_score:
            best_score = score
            best_cat = cat_id

    if best_cat is None or best_score == 0:
        return "cat15"  # הלכות שונות fallback

    return best_cat


def extract_qa_pairs(messages, roles):
    """
    Extract Q&A pairs from classified messages.
    A Q&A pair is: one or more question messages (שואל) followed by
    one or more rabbi answer messages (הרב).
    """
    qa_pairs = []
    i = 0
    n = len(messages)

    while i < n:
        # Look for a question
        if roles[i] != "שואל":
            i += 1
            continue

        # Collect consecutive question messages
        question_parts = []
        question_sender = messages[i][1]
        question_ts = messages[i][0]
        question_msg_idx = i  # index into raw messages for linking

        while i < n and roles[i] == "שואל":
            ts, sender, text = messages[i]
            # Stop if a different sender starts asking — that's a new question
            if sender != question_sender and sender != "שו״ת יחדיו" and question_sender != "שו״ת יחדיו":
                break
            if text.strip() and text.strip() != "[media]":
                question_parts.append(text.strip())
            if not question_sender or question_sender == "שו״ת יחדיו":
                question_sender = sender
            i += 1

        if not question_parts:
            continue

        # Skip reactions/riddles and non-question messages from other senders.
        # Real questions from other senders (containing '?') are NOT skipped —
        # they block pairing so they can be processed as their own Q&A.
        while i < n and (roles[i] in ("תגובה", "חידה") or
                         (roles[i] == "שואל" and messages[i][1] != question_sender
                          and '?' not in messages[i][2])):
            i += 1

        # Look for rabbi's answer
        if i >= n or roles[i] != "הרב":
            continue

        # Collect consecutive rabbi answer messages
        answer_parts = []
        while i < n and roles[i] == "הרב":
            ts, sender, text = messages[i]
            if text.strip() and text.strip() != "[media]":
                answer_parts.append(text.strip())
            i += 1

        if not answer_parts:
            continue

        question_text = "\n".join(question_parts)
        answer_text = "\n".join(answer_parts)

        # Skip very short questions (greetings only) or media-only
        if len(question_text.replace("[media]", "").strip()) < 5:
            continue

        # Skip if answer is too short (just "כן" etc. without context)
        # Actually keep these — they are valid answers

        # Build the QA pair
        qa = {
            "date": question_ts[:10],  # YYYY-MM-DD
            "question": question_text,
            "answer": answer_text,
            "questioner": get_sender_name(question_sender),
            "msg_idx": question_msg_idx,  # raw message index for linking
            "followups": [],
        }

        # Look for follow-up Q&A in the same conversation
        # (question followed by answer within a few messages)
        followup_count = 0
        while i < n and followup_count < 3:
            # Skip reactions
            j = i
            while j < n and roles[j] == "תגובה":
                j += 1

            if j >= n or roles[j] != "שואל":
                break

            # Check if this follow-up is close in time (within 30 min)
            follow_ts = messages[j][0]
            if not _is_close_in_time(qa["date"], follow_ts[:10], question_ts, follow_ts):
                break

            # Collect follow-up question
            fu_q_parts = []
            while j < n and roles[j] == "שואל":
                ts, sender, text = messages[j]
                if text.strip() and text.strip() != "[media]":
                    fu_q_parts.append(text.strip())
                j += 1

            if not fu_q_parts:
                i = j
                break

            # Skip reactions
            while j < n and roles[j] in ("תגובה", "חידה"):
                j += 1

            # Collect follow-up answer
            if j >= n or roles[j] != "הרב":
                i = j
                break

            fu_a_parts = []
            while j < n and roles[j] == "הרב":
                ts, sender, text = messages[j]
                if text.strip() and text.strip() != "[media]":
                    fu_a_parts.append(text.strip())
                j += 1

            if fu_a_parts:
                qa["followups"].append({
                    "question": "\n".join(fu_q_parts),
                    "answer": "\n".join(fu_a_parts),
                })
                followup_count += 1

            i = j

        qa_pairs.append(qa)

    return qa_pairs


def _is_close_in_time(date1, date2, ts1, ts2):
    """Check if two messages are on the same day (close enough for follow-up)."""
    return date1 == date2


def escape_html(text):
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace('\n', '<br>'))


def format_date(yyyy_mm_dd):
    """Convert YYYY-MM-DD to DD.MM.YYYY"""
    parts = yyyy_mm_dd.split('-')
    return f"{parts[2]}.{parts[1]}.{parts[0]}"


def build_qa_html(qa_pairs_by_cat):
    """Build the complete Q&A section HTML (categories + TOC)."""
    # Get category info
    cat_lookup = {cat_id: (cat_name, kws) for cat_id, cat_name, kws in ALL_CATEGORIES}

    # Determine which categories have content
    active_cats = []
    for cat_id, cat_name, _ in ALL_CATEGORIES:
        pairs = qa_pairs_by_cat.get(cat_id, [])
        if pairs:
            active_cats.append((cat_id, cat_name, pairs))

    # Build TOC
    toc_lines = []
    for idx, (cat_id, cat_name, pairs) in enumerate(active_cats, 1):
        toc_lines.append(
            f'    <a href="#{cat_id}"><span class="toc-num">{idx}</span> '
            f'{cat_name} <span class="toc-count">({len(pairs)})</span></a>'
        )
    toc_html = '\n'.join(toc_lines)

    # Build category sections
    sections = []
    for idx, (cat_id, cat_name, pairs) in enumerate(active_cats, 1):
        # Sort by date descending (newest first)
        pairs.sort(key=lambda p: p["date"], reverse=True)

        items = []
        for qa in pairs:
            date_str = format_date(qa["date"])
            q_html = escape_html(qa["question"])
            a_html = escape_html(qa["answer"])
            msg_idx = qa.get("msg_idx", 0)

            item = f'''    <div class="qa-item">
      <span class="qa-date">{date_str}</span>
      <a class="qa-raw-link" href="#raw-messages" onclick="showInContext({msg_idx}, true)" title="צפה בהודעה המקורית בהקשר המלא">📜 הודעה מקורית</a>
      <div class="qa-question">{q_html}</div>
      <div class="qa-answer">{a_html}</div>'''

            for fu in qa.get("followups", []):
                fu_q = escape_html(fu["question"])
                fu_a = escape_html(fu["answer"])
                item += f'''
      <div class="qa-followup">{fu_q}</div>
      <div class="qa-followup-answer">{fu_a}</div>'''

            item += '\n    </div>'
            items.append(item)

        items_html = '\n\n'.join(items)

        section = f'''<!-- Category {idx}: {cat_name} -->
<section class="category" id="{cat_id}">
  <div class="category-header">
    <span class="cat-num">{idx}</span>
    <h2>{cat_name}</h2>
  </div>
  <div class="qa-list">

{items_html}

  </div>
</section>'''
        sections.append(section)

    total_qa = sum(len(pairs) for _, _, pairs in active_cats)
    return toc_html, '\n\n'.join(sections), total_qa, active_cats


def update_html(toc_html, sections_html, total_qa, active_cats, first_date, last_date):
    """Update the HTML file with new Q&A content."""
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # Update header date range
    html = re.sub(
        r'<div class="date-range">.*?</div>',
        f'<div class="date-range">תקופה: אוגוסט 2024 &ndash; אפריל 2026 &nbsp;|&nbsp; '
        f'{total_qa} שאלות ותשובות &nbsp;|&nbsp; עדכון אחרון: {format_date(last_date)}</div>',
        html
    )

    # Replace TOC
    html = re.sub(
        r'(<div class="toc-grid">)\n.*?(</div>\n</nav>)',
        f'\\1\n{toc_html}\n  \\2',
        html,
        flags=re.DOTALL
    )

    # Replace all category sections
    # Find the start of first category and the closing </div> after last </section>
    cat_start = re.search(r'<!-- Category 1:', html)
    raw_start = html.find('<!-- RAW MESSAGES SECTION -->')
    if raw_start == -1:
        raw_start = html.find('<div class="footer">')

    if cat_start and raw_start > 0:
        # Find the last </section> before raw section
        last_section_end = html.rfind('</section>', cat_start.start(), raw_start)
        if last_section_end > 0:
            last_section_end = last_section_end + len('</section>')
            before = html[:cat_start.start()]
            after = html[last_section_end:]
            html = before + sections_html + '\n' + after

    # Update footer
    html = re.sub(
        r'(<div class="footer">).*?(</div>)',
        f'\\1\n  שו״ת יחדיו — שאלות ותשובות מאת הרב אייל ורד — {total_qa} שאלות ותשובות\n\\2',
        html,
        flags=re.DOTALL
    )

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    return total_qa


def main():
    # Parse raw messages
    with open(RAW_PATH, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    messages = parse_messages(raw_text)
    print(f"Parsed {len(messages)} messages")

    # Classify roles
    roles = classify_all_messages(messages)
    role_counts = {}
    for r in roles:
        role_counts[r] = role_counts.get(r, 0) + 1
    print(f"Roles: {dict(sorted(role_counts.items()))}")

    # Extract Q&A pairs
    qa_pairs = extract_qa_pairs(messages, roles)
    print(f"\nExtracted {len(qa_pairs)} Q&A pairs")

    # Categorize
    qa_by_cat = {}
    for qa in qa_pairs:
        cat = categorize_qa(qa["question"], qa["answer"])
        qa_by_cat.setdefault(cat, []).append(qa)

    # Print summary
    cat_lookup = {c[0]: c[1] for c in ALL_CATEGORIES}
    for cat_id in sorted(qa_by_cat.keys()):
        print(f"  {cat_id} ({cat_lookup.get(cat_id, '?')}): {len(qa_by_cat[cat_id])} pairs")

    # Date range
    dates = [qa["date"] for qa in qa_pairs]
    first_date = min(dates)
    last_date = max(dates)
    print(f"\nDate range: {first_date} to {last_date}")

    # Build HTML
    toc_html, sections_html, total_qa, active_cats = build_qa_html(qa_by_cat)

    # Update the HTML file
    update_html(toc_html, sections_html, total_qa, active_cats, first_date, last_date)
    print(f"\nUpdated HTML with {total_qa} Q&A pairs across {len(active_cats)} categories")


if __name__ == '__main__':
    main()
