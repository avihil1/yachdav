#!/usr/bin/env python3
"""
Rebuild the raw messages section in the HTML with:
- Prominent placement before footer
- Search box with live filtering
- Heuristic role detection (rabbi / questioner / reaction)
- Color-coded roles with display badges
- Each message as a styled card
"""
import re
import hashlib

HTML_PATH = "/Users/hillelk/Documents/shut-yachdav/shut-yachdav-qa.html"
RAW_PATH = "/Users/hillelk/Documents/shut-yachdav/raw_messages.txt"

# Known rabbi sender names (from WhatsApp export and MCP)
RABBI_SENDERS = {
    "Harav Eyal Vered",
    "הרב אייל ורד",
    "112124500119757",      # Rabbi's phone number (MCP format)
    "+972 54-462-6779",     # Rabbi's phone in export format
}

# Role colors
ROLE_COLORS = {
    "הרב": "#1a6b3c",       # green
    "שואל": "#2d5f8a",      # blue
    "תגובה": "#888888",     # gray
    "חידה": "#8b4513",      # brown (riddles)
}

# --- Heuristic role classification ---

# Greeting patterns that address the rabbi (strong question signal)
GREETING_RABBI_RE = re.compile(
    r'^(שלום הרב|בוקר טוב הרב|ערב טוב הרב|הרב שלום|שלום כבוד הרב|'
    r'שבוע טוב.*הרב|הרב,|שלום וברכה)',
    re.MULTILINE
)

# Question content patterns
QUESTION_CONTENT_RE = re.compile(
    r'(האם מותר|האם יש|האם ניתן|האם צריך|מה דין|מה הדין|'
    r'מה ההנחיות|מה מברכים|האם אפשר|רציתי לשאול|רצינו לשאול|'
    r'אשמח לדעת|אשמח אם אפשר|הרב יכול להסביר|'
    r'מה לגבי|מה עם|איזו ברכה|האם כדי|מה עושים|'
    r'שאלה[:\s]|גם לי שאלה|עוד שאלה|שאלה \(דחופה\))'
)

# Thank-you / short reaction patterns
# Allow optional repeated "רבה" and "הרב" / "רב" suffix
# Match just the first line — multiline messages starting with thanks are handled separately
THANKS_RE = re.compile(
    r'^(תודה|ישר כח|יישר כח|תודה רבה|תודה הרב|🎯+|הבנתי\.?|ברור\.?|'
    r'כך חשבתי|אכן|מעולה|נהדר|יופי|אמן)'
    r'(\s+רבה)*'  # allow repeated "רבה"
    r'(\s+(הרב|רב))?[\s!.🙏]*$',
    re.MULTILINE
)

# Broader thanks detection for multiline messages that START with thanks
# (the main content is gratitude, not a question)
THANKS_START_RE = re.compile(
    r'^(תודה|ישר כח|יישר כח|תודה רבה|תודה הרב)'
    r'(\s+רבה)*'
    r'(\s+(הרב|רב))?[\s!.🙏]*\n',
)

# Rabbi's riddle pattern
RIDDLE_RE = re.compile(r'חידת רש[״"]י')

# Rabbi authoritative answer patterns
RABBI_RULING_RE = re.compile(
    r'(לכתחילה|בדיעבד|לכולי עלמא|כלי שני|כלי שלישי|'
    r'בשולחן ערוך|הרב עובדיה|במסכת |'
    r'שהכל נהיה בדברו|המוציא לחם|בורא מיני מזונות|'
    r'מברכים עליה|מברכים על|'
    r'יש להמנע|יש להקפיד|אין מניעה|אין בזה בעיה|'
    r'שאריות מזון|טעם פגום|הטעם פגום|'
    r'ניתן יהיה|מותר יהיה|'
    r'כמבואר ב|כידוע|כפי ש|שנאמר|'
    r'זו זכות גדולה|ודאי מותר|ודאי\.)'
)

# Short authoritative one-liners typical of rabbi
RABBI_SHORT_RE = re.compile(
    r'^(מותר|אסור|נכון|נכון מאוד|כן\.?|לא\.?|אין צורך|מספיק|'
    r'אין בזה בעיה|אין\.?|מצטרפים|אין עדיפות)[\s.!]*$'
)

# Clarifying question from rabbi (short, no greeting)
RABBI_CLARIFY_RE = re.compile(
    r'^(הסיר בן יומו|הופעה של מי|אולי תפרט|כלומר|'
    r'בן יומו\?|את מי\?|של מי\?)[\s?]*$'
)

# Rabbi continuation markers
RABBI_CONTINUATION_RE = re.compile(
    r'^(ולכן|אמנם|ממילא|כלומר|כמו כן|הבהרה|אך |'
    r'שאלה מצויינת|שאלות יפות|תראו כמה|עדיין לא|'
    r'גם זו תשובה|זו תשובה|נפלא|'
    r'מחילה\.)'
)


def classify_role(text, raw_sender, idx, messages):
    """
    Classify a message's role as הרב (rabbi), שואל (questioner),
    תגובה (reaction/thanks), or חידה (riddle).

    Key principle: הרב is DETERMINISTIC — only known rabbi senders
    (by name or phone) are classified as הרב. No heuristics needed.
    For everyone else, we only distinguish שואל vs תגובה.
    """
    clean = text.strip()
    has_question_mark = '?' in clean

    # === DETERMINISTIC: Known rabbi senders ===
    if raw_sender in RABBI_SENDERS:
        if RIDDLE_RE.search(clean):
            return "חידה"
        return "הרב"

    # === For channel account "שו״ת יחדיו" (MCP data) — also check heuristic ===
    # Only the channel account needs rabbi heuristics; named senders are never the rabbi
    is_channel = raw_sender == "שו״ת יחדיו"

    # --- From here on, sender is a community member (or channel account) ---

    # 1. Riddle
    if RIDDLE_RE.search(clean):
        return "חידה"

    # 2. Thank-you / short reaction (single-line)
    if THANKS_RE.match(clean):
        return "תגובה"

    # 3. Multiline message starting with thanks — treat as reaction
    if THANKS_START_RE.match(clean) and not has_question_mark:
        return "תגובה"

    # 4. Emoji-only messages
    if len(clean) <= 10 and not re.search(r'[\u0590-\u05FFa-zA-Z]', clean):
        return "תגובה"

    # 5. Question — greeting the rabbi
    if GREETING_RABBI_RE.search(clean):
        return "שואל"

    # 6. Question — content patterns
    if QUESTION_CONTENT_RE.search(clean):
        return "שואל"

    # 7. Any message with a question mark → שואל
    if has_question_mark:
        return "שואל"

    # --- No question mark from here on ---

    # For named community members (not channel account): never classify as הרב
    if not is_channel:
        # Short → reaction, long → probably a comment/שואל
        if len(clean) < 60:
            return "תגובה"
        return "שואל"

    # === Channel account heuristics (MCP data only) ===
    # These messages are anonymized — could be rabbi or community member

    # 8. Rabbi short authoritative answer (מותר, אסור, כן, לא)
    if RABBI_SHORT_RE.match(clean):
        return "הרב"

    # 9. Rabbi clarifying question
    if RABBI_CLARIFY_RE.match(clean):
        return "הרב"

    # 10. Rabbi continuation markers
    if RABBI_CONTINUATION_RE.match(clean):
        return "הרב"

    # 11. Rabbi ruling language in longer messages
    if RABBI_RULING_RE.search(clean) and len(clean) > 40:
        return "הרב"

    # 12. Context-based heuristics (channel account only)
    if idx > 0:
        prev_role = _prev_roles.get(idx - 1)

        # After a question, a substantive response is likely the rabbi
        if prev_role == "שואל" and len(clean) > 60:
            return "הרב"

        # After rabbi's answer, short message is a reaction
        if prev_role == "הרב" and len(clean) < 60:
            return "תגובה"

    # 13. Long messages without question marks — likely rabbi
    if len(clean) > 100:
        return "הרב"

    # 14. Default
    if len(clean) < 60:
        return "תגובה"

    return "הרב"


# Cache for previous roles during classification
_prev_roles = {}


def classify_all_messages(messages):
    """Classify all messages and return list of roles."""
    global _prev_roles
    _prev_roles = {}
    roles = []
    for idx, (ts, sender, text) in enumerate(messages):
        role = classify_role(text, sender, idx, messages)
        _prev_roles[idx] = role
        roles.append(role)
    return roles


def get_sender_name(raw_sender):
    """Map raw sender to display name."""
    if raw_sender in RABBI_SENDERS:
        return "הרב אייל ורד"
    if raw_sender == "Me":
        return "הלל"
    return raw_sender


def get_sender_color(name):
    if name == "הרב אייל ורד":
        return "#1a6b3c"
    h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
    return f"hsl({h % 360}, 55%, 35%)"


def parse_messages(raw_text):
    lines = raw_text.strip().split('\n')
    messages = []
    current_lines = []
    current_meta = None

    for line in lines:
        m = re.match(r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] Chat: .+ From: ([^:]+): (.*)$', line)
        if m:
            if current_meta:
                messages.append(current_meta + (('\n'.join(current_lines)),))
            ts, sender, text = m.group(1), m.group(2), m.group(3)
            current_meta = (ts, sender)
            current_lines = [text]
        else:
            current_lines.append(line)

    if current_meta:
        messages.append(current_meta + (('\n'.join(current_lines)),))

    return messages


def escape_html(text):
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace('\n', '<br>'))


def build_raw_section(messages):
    roles = classify_all_messages(messages)

    # Count roles
    role_counts = {}
    for r in roles:
        role_counts[r] = role_counts.get(r, 0) + 1

    # Build legend HTML — role-based
    legend_items = []
    role_legend = [
        ("הרב", ROLE_COLORS["הרב"], "תשובות הרב"),
        ("שואל", ROLE_COLORS["שואל"], "שאלות"),
        ("תגובה", ROLE_COLORS["תגובה"], "תגובות"),
        ("חידה", ROLE_COLORS["חידה"], "חידות רש״י"),
    ]
    for role_key, color, label in role_legend:
        count = role_counts.get(role_key, 0)
        if count > 0:
            legend_items.append(
                f'<span class="raw-legend-item" style="border-right: 3px solid {color}; padding-right: 6px; margin-left: 12px;">'
                f'{escape_html(label)} ({count})</span>'
            )
    legend_html = ' '.join(legend_items)

    # Build message cards
    msg_cards = []
    for idx, (ts, raw_sender, text) in enumerate(messages):
        role = roles[idx]
        role_color = ROLE_COLORS.get(role, "#888")
        name = get_sender_name(raw_sender)
        sender_color = get_sender_color(name)
        date_str = ts[:10]
        time_str = ts[11:16]
        escaped_text = escape_html(text)

        # Role badge
        role_label = {
            "הרב": "הרב",
            "שואל": "שואל",
            "תגובה": "תגובה",
            "חידה": "חידה",
        }.get(role, role)

        # Show sender name with their consistent color
        sender_display = ""
        if role not in ("הרב", "חידה"):
            sender_display = f' <span class="raw-msg-name" style="color:{sender_color}">{escape_html(name)}</span>'

        msg_cards.append(f'''<div class="raw-msg" id="raw-msg-{idx}" data-role="{role}" data-sender="{escape_html(name)}" data-text="{escape_html(text.lower())}" style="border-right-color:{sender_color}" onclick="showInContext({idx})">
<div class="raw-msg-header">
<span class="raw-msg-role" style="background:{role_color}">{role_label}</span>{sender_display}
<span class="raw-msg-time">{date_str} {time_str}</span>
</div>
<div class="raw-msg-text">{escaped_text}</div>
</div>''')

    messages_html = '\n'.join(msg_cards)

    return f'''
<!-- RAW MESSAGES SECTION -->
<style>
  .raw-section {{
    max-width: 900px;
    margin: 2rem auto;
    padding: 0 1rem;
  }}
  .raw-section-title {{
    font-family: 'Frank Ruhl Libre', serif;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--primary);
    text-align: center;
    margin-bottom: 0.5rem;
  }}
  .raw-section-subtitle {{
    text-align: center;
    color: var(--text-light);
    font-size: 0.9rem;
    margin-bottom: 1rem;
  }}
  .raw-search-box {{
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 1rem;
    font-family: 'Heebo', sans-serif;
    border: 2px solid var(--border);
    border-radius: 8px;
    direction: rtl;
    background: var(--card-bg);
    transition: border-color 0.2s;
    margin-bottom: 0.75rem;
  }}
  .raw-search-box:focus {{
    outline: none;
    border-color: var(--primary-light);
  }}
  .raw-filter-buttons {{
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }}
  .raw-filter-btn {{
    padding: 0.35rem 0.75rem;
    border: 2px solid var(--border);
    border-radius: 20px;
    background: var(--card-bg);
    cursor: pointer;
    font-size: 0.85rem;
    font-family: 'Heebo', sans-serif;
    transition: all 0.2s;
  }}
  .raw-filter-btn:hover {{
    border-color: var(--primary-light);
  }}
  .raw-filter-btn.active {{
    color: white;
    border-color: transparent;
  }}
  .raw-search-stats {{
    text-align: center;
    color: var(--text-light);
    font-size: 0.85rem;
    margin-bottom: 0.75rem;
  }}
  .raw-legend {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.25rem 0;
    margin-bottom: 1rem;
    font-size: 0.85rem;
    color: var(--text);
  }}
  .raw-legend-item {{
    white-space: nowrap;
  }}
  .raw-messages-container {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    max-height: 70vh;
    overflow-y: auto;
    box-shadow: var(--shadow);
  }}
  .raw-msg {{
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.5rem;
    border-radius: 8px;
    background: var(--bg);
    border-right: 3px solid #ccc;
    transition: background 0.15s;
  }}
  /* border-right color set inline per sender */
  .raw-msg:hover {{
    background: #f0f4f8;
  }}
  .raw-msg.clickable {{
    cursor: pointer;
  }}
  .raw-msg.clickable:hover {{
    background: #e8eef4;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }}
  .raw-msg-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.25rem;
    gap: 0.5rem;
  }}
  .raw-msg-role {{
    display: inline-block;
    color: white;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.1rem 0.5rem;
    border-radius: 10px;
    white-space: nowrap;
  }}
  .raw-msg-name {{
    font-size: 0.8rem;
    color: var(--text-light);
    font-weight: 500;
  }}
  .raw-msg-time {{
    font-size: 0.75rem;
    color: var(--text-light);
    direction: ltr;
    font-family: monospace;
    margin-right: auto;
  }}
  .raw-msg-text {{
    font-size: 0.9rem;
    line-height: 1.5;
    word-break: break-word;
  }}
  .raw-msg.hidden {{
    display: none;
  }}
  .raw-msg mark {{
    background: #fff3a8;
    padding: 0 2px;
    border-radius: 2px;
  }}
  .raw-msg.highlight {{
    animation: highlightPulse 2s ease-out;
  }}
  @keyframes highlightPulse {{
    0% {{ background: #fff3a8; box-shadow: 0 0 0 3px #c9a84c; }}
    100% {{ background: var(--bg); box-shadow: none; }}
  }}
  .raw-section hr {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0 1rem;
  }}
  .raw-note {{
    text-align: center;
    color: var(--text-light);
    font-size: 0.8rem;
    margin-top: 0.5rem;
    font-style: italic;
  }}
</style>

<div class="raw-section" id="raw-messages">
  <hr>
  <div class="raw-section-title">הודעות גולמיות</div>
  <div class="raw-section-subtitle">
    {len(messages)} הודעות &mdash; אוגוסט 2024 עד אפריל 2026
  </div>

  <input type="text" class="raw-search-box" id="rawSearch" placeholder="חיפוש בהודעות..." oninput="filterRawMessages()">

  <div class="raw-filter-buttons">
    <button class="raw-filter-btn active" data-filter="all" onclick="setRoleFilter('all', this)" style="border-color: var(--primary);">הכל</button>
    <button class="raw-filter-btn" data-filter="הרב" onclick="setRoleFilter('הרב', this)">תשובות הרב</button>
    <button class="raw-filter-btn" data-filter="שואל" onclick="setRoleFilter('שואל', this)">שאלות</button>
    <button class="raw-filter-btn" data-filter="תגובה" onclick="setRoleFilter('תגובה', this)">תגובות</button>
    <button class="raw-filter-btn" data-filter="חידה" onclick="setRoleFilter('חידה', this)">חידות</button>
  </div>

  <div class="raw-search-stats" id="rawSearchStats"></div>

  <div class="raw-legend">{legend_html}</div>

  <div class="raw-messages-container" id="rawMessagesContainer">
{messages_html}
  </div>
  <div class="raw-note">סיווג התפקידים (שואל/הרב/תגובה) מבוסס על ניתוח תוכן אוטומטי — ייתכנו אי-דיוקים</div>
</div>

<script>
var currentRoleFilter = 'all';
function showInContext(msgIdx, fromQA) {{
  // When called from raw section search results, only act if filter is active
  if (!fromQA) {{
    var q = document.getElementById('rawSearch').value.trim();
    if (!q && currentRoleFilter === 'all') return;
  }}

  // Clear search and reset filter to show all messages
  document.getElementById('rawSearch').value = '';
  currentRoleFilter = 'all';
  document.querySelectorAll('.raw-filter-btn').forEach(b => {{
    b.classList.remove('active');
    b.style.background = '';
    b.style.color = '';
    b.style.borderColor = '';
  }});
  var allBtn = document.querySelector('.raw-filter-btn[data-filter=\"all\"]');
  if (allBtn) {{ allBtn.classList.add('active'); allBtn.style.borderColor = 'var(--primary)'; }}
  filterRawMessages();

  // Scroll to the clicked message and highlight it
  var el = document.getElementById('raw-msg-' + msgIdx);
  if (el) {{
    el.classList.remove('highlight');
    void el.offsetWidth; // force reflow for re-triggering animation
    el.classList.add('highlight');
    el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  }}
}}
function setRoleFilter(role, btn) {{
  currentRoleFilter = role;
  document.querySelectorAll('.raw-filter-btn').forEach(b => {{
    b.classList.remove('active');
    b.style.background = '';
    b.style.color = '';
    b.style.borderColor = '';
  }});
  btn.classList.add('active');
  var colors = {{'הרב':'#1a6b3c','שואל':'#2d5f8a','תגובה':'#888888','חידה':'#8b4513'}};
  if (role === 'all') {{
    btn.style.borderColor = 'var(--primary)';
  }} else {{
    btn.style.background = colors[role] || '#888';
    btn.style.color = 'white';
    btn.style.borderColor = 'transparent';
  }}
  filterRawMessages();
}}
function filterRawMessages() {{
  const q = document.getElementById('rawSearch').value.trim().toLowerCase();
  const msgs = document.querySelectorAll('.raw-msg');
  const isFiltered = q || currentRoleFilter !== 'all';
  let shown = 0;
  msgs.forEach(m => {{
    const role = m.getAttribute('data-role') || '';
    const sender = (m.getAttribute('data-sender') || '').toLowerCase();
    const text = (m.getAttribute('data-text') || '');
    const roleMatch = currentRoleFilter === 'all' || role === currentRoleFilter;
    const textMatch = !q || sender.includes(q) || text.includes(q);
    const match = roleMatch && textMatch;
    m.classList.toggle('hidden', !match);
    m.classList.toggle('clickable', isFiltered && match);
    if (match) shown++;
    const textEl = m.querySelector('.raw-msg-text');
    if (q && match) {{
      const original = textEl.getAttribute('data-original') || textEl.innerHTML.replace(/<mark>/g, '').replace(/<\\/mark>/g, '');
      if (!textEl.getAttribute('data-original')) textEl.setAttribute('data-original', textEl.innerHTML);
      const regex = new RegExp('(' + q.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
      textEl.innerHTML = original.replace(regex, '<mark>$1</mark>');
    }} else if (textEl.getAttribute('data-original')) {{
      textEl.innerHTML = textEl.getAttribute('data-original');
      textEl.removeAttribute('data-original');
    }}
  }});
  const stats = document.getElementById('rawSearchStats');
  if (isFiltered) {{
    stats.textContent = 'מציג ' + shown + ' מתוך ' + msgs.length + ' הודעות — לחץ על הודעה לצפייה בהקשר';
  }} else {{
    stats.textContent = '';
  }}
}}
</script>
<!-- END RAW MESSAGES SECTION -->
'''


def main():
    with open(RAW_PATH, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    messages = parse_messages(raw_text)
    print(f"Parsed {len(messages)} messages")

    roles = classify_all_messages(messages)
    role_counts = {}
    for r in roles:
        role_counts[r] = role_counts.get(r, 0) + 1
    print(f"Role breakdown: {dict(sorted(role_counts.items()))}")

    raw_section = build_raw_section(messages)

    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remove old raw section if present (both old details format and new div format)
    html = re.sub(
        r'\n*<div class="container">\s*<details class="raw-log">.*?</details>\s*</div>\n*',
        '\n',
        html,
        flags=re.DOTALL
    )
    html = re.sub(
        r'\n*<!-- RAW MESSAGES SECTION -->.*?<!-- END RAW MESSAGES SECTION -->\n*',
        '\n',
        html,
        flags=re.DOTALL
    )

    # Insert new section before footer
    html = html.replace('<div class="footer">', raw_section + '\n<div class="footer">')

    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Injected raw section with {len(messages)} messages and role tagging")


if __name__ == '__main__':
    main()
