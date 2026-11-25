"""Reading-text projection of the pinned LSG OSIS milestone fragments.

Preserve the legacy source punctuation and whitespace policy. Exclude complete
editorial title elements, not merely their markup. Canonical titles are not
editorial and must not be discarded. Unknown title classifications fail closed.
"""
import re

NOTE = re.compile(r"<note\b[^>]*>.*?</note>", re.S)
TITLE = re.compile(r"<title\b([^>]*)>(.*?)</title>", re.S)
TAG = re.compile(r"<[^>]+>")
TOKEN = re.compile(r"[^\W\d_]+(?:[’'\-][^\W\d_]+)*")

def reading_prose(fragment):
    prose = NOTE.sub("", fragment)
    def remove_editorial(match):
        attrs = match.group(1).strip()
        if re.search(r'\bcanonical\s*=\s*["\x27]true["\x27]', attrs):
            return match.group(0)
        if attrs in ('', 'type="parallel"'):
            return ""
        raise ValueError(f"Unclassified title attributes: {attrs}")
    prose = TITLE.sub(remove_editorial, prose)
    return TAG.sub("", prose).strip()

def legacy_prose(fragment):
    return TAG.sub("", NOTE.sub("", fragment)).strip()
