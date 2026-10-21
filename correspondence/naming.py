"""Scan filename conventions, independent of storage and historical metadata."""
from datetime import date
import re


PAGE = re.compile(r"^(.*?)(?:[ ]*\(([A-Za-z]+|\d+)\)|_(\d+))$")
STEM = re.compile(
    r"^(?P<sender>[^-]+)-(?P<recipient>[^-]+)-"
    r"(?P<date>\d{8}|\d{6}|\d{4}(?:-\d{1,2}){0,2}|undated)"
    r"(?:-(?P<letter_suffix>[a-z]+))?$"
)


def split_page(stem):
    """Keep the exact group stem; accept current numeric and legacy page labels."""
    match = PAGE.fullmatch(stem)
    return (match[1], (match[2] or match[3]).upper()) if match else (stem, None)


def filename_hints(stem):
    """Normalize date formatting only, without filling in missing date components."""
    match = STEM.fullmatch(stem)
    if not match:
        return {}
    hints = {k: v for k, v in match.groupdict().items() if v is not None}
    value = hints['date']
    if value == 'undated':
        hints['date'] = None
        return hints
    parts = value.split('-') if '-' in value else [value[:4], *[value[i:i+2] for i in range(4, len(value), 2)]]
    try:
        numbers = [int(p) for p in parts]
        date(*(numbers + [1] * (3 - len(numbers))))
    except ValueError:
        return {}
    hints['date'] = '-'.join([f'{numbers[0]:04d}', *[f'{n:02d}' for n in numbers[1:]]])
    return hints


def canonical_stem(stem):
    """Format a recognized letter stem, leaving custom report titles intact."""
    hints = filename_hints(stem)
    if not hints:
        return stem
    value = hints['date'].replace('-', '') if hints['date'] else 'undated'
    suffix = '-' + hints['letter_suffix'] if hints.get('letter_suffix') else ''
    return f"{hints['sender']}-{hints['recipient']}-{value}{suffix}"
