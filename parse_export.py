#!/usr/bin/env python3
"""
Parse WhatsApp chat export file and convert to raw_messages.txt format.
Export format: DD/MM/YYYY, HH:MM - SENDER: MESSAGE
Our format:   [YYYY-MM-DD HH:MM:SS] Chat: שו״ת יחדיו From: SENDER: MESSAGE
"""
import re
import sys
from datetime import datetime

EXPORT_PATH = "/Users/hillelk/Downloads/WhatsApp Chat with שו״ת יחדיו.txt"
RAW_PATH = "/Users/hillelk/Documents/shut-yachdav/raw_messages.txt"
CHAT_NAME = "שו״ת יחדיו"

# Regex for WhatsApp export message line
# Format: DD/MM/YYYY, HH:MM - SENDER: MESSAGE
MSG_RE = re.compile(r'^(\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}) - (.+?)(?:: (.*))?$')

# System messages to skip (no colon after sender = system event)
SKIP_PATTERNS = [
    'joined using',
    'was added',
    'added ',
    'created group',
    'Messages and calls are end-to-end encrypted',
    'You joined using',
    'This group has over',
    'changed the group',
    'changed this group',
    'changed the subject',
    'changed the description',
    'left',
    'removed',
    'settings',
    "group's invite link",
    'security code changed',
    'admin',
    'disappearing messages',
    'pinned a message',
]

# Content to mark as media
MEDIA_MARKERS = {
    '<Media omitted>': '[media]',
    'This message was deleted': None,  # Skip deleted messages
    'null': None,
}


def parse_export(filepath):
    """Parse WhatsApp export file, return list of (timestamp, sender, text)."""
    messages = []
    current_msg = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')

            m = MSG_RE.match(line)
            if m:
                # Save previous message
                if current_msg:
                    messages.append(current_msg)

                date_str, time_str, sender, text = m.group(1), m.group(2), m.group(3), m.group(4)

                # System message (no text after sender — the regex captures None)
                if text is None:
                    # Check if this is a system event
                    current_msg = None
                    continue

                # Check if sender line is actually a system message
                is_system = False
                full_line = f"{sender}: {text}" if text else sender
                for pattern in SKIP_PATTERNS:
                    if pattern in full_line:
                        is_system = True
                        break
                if is_system:
                    current_msg = None
                    continue

                # Skip deleted messages
                if text.strip() in ('This message was deleted', 'null', ''):
                    current_msg = None
                    continue

                # Clean up edited message marker
                text = text.replace(' <This message was edited>', '')

                # Convert media markers
                if text.strip() == '<Media omitted>':
                    text = '[media]'

                # Parse date: DD/MM/YYYY -> YYYY-MM-DD
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
                    ts = dt.strftime("%Y-%m-%d %H:%M:00")
                except ValueError:
                    current_msg = None
                    continue

                # Clean sender name (remove RTL/LTR marks and ~ prefix)
                sender = sender.strip()
                sender = re.sub(r'[\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]', '', sender)
                sender = re.sub(r'^~\s*', '', sender)
                sender = sender.strip('‎‫‬')  # Remove additional unicode marks
                sender = sender.strip()

                current_msg = (ts, sender, text)
            else:
                # Continuation line — append to current message
                if current_msg:
                    ts, sender, text = current_msg
                    current_msg = (ts, sender, text + '\n' + line)

    # Don't forget the last message
    if current_msg:
        messages.append(current_msg)

    return messages


def write_raw_messages(messages, filepath):
    """Write messages in our raw_messages.txt format."""
    with open(filepath, 'w', encoding='utf-8') as f:
        for i, (ts, sender, text) in enumerate(messages):
            line = f"[{ts}] Chat: {CHAT_NAME} From: {sender}: {text}"
            if i < len(messages) - 1:
                f.write(line + '\n')
            else:
                f.write(line)


def main():
    messages = parse_export(EXPORT_PATH)

    # Stats
    senders = {}
    for ts, sender, text in messages:
        senders[sender] = senders.get(sender, 0) + 1

    print(f"Parsed {len(messages)} messages")
    print(f"Date range: {messages[0][0]} to {messages[-1][0]}")
    print(f"\nTop senders:")
    for sender, count in sorted(senders.items(), key=lambda x: -x[1])[:20]:
        print(f"  {count:4d}  {sender}")

    write_raw_messages(messages, RAW_PATH)
    print(f"\nWritten to {RAW_PATH}")


if __name__ == '__main__':
    main()
