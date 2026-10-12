"""Read-only grouping on analyst-entered case metadata, never source text."""
from datetime import UTC, datetime
from typing import Literal, get_args

Governorate = Literal['aleppo', 'damascus', 'rural-damascus', 'daraa', 'deir-ez-zor',
                      'hama', 'hasakah', 'homs', 'idlib', 'latakia', 'quneitra',
                      'raqqa', 'suwayda', 'tartus']
GOVERNORATES = frozenset(get_args(Governorate))
WINDOW_SECONDS = 6 * 60 * 60


def event_time(fields):
    if not isinstance(fields, dict):
        return None
    value = fields.get('occurred_at')
    if not isinstance(value, str):
        return None
    try:
        timestamp = datetime.fromisoformat(value)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return None
        return timestamp.astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def grouping_metadata(case):
    fields = case.fields
    timestamp = event_time(fields)
    if timestamp is None or case.state == 'withdrawn':
        return None
    governorate = fields.get('private_governorate')
    category = fields.get('category')
    if not isinstance(governorate, str) or governorate not in GOVERNORATES or not isinstance(category, str) or not category:
        return None
    return timestamp, governorate, category


def related_cases(current, candidates):
    metadata = grouping_metadata(current)
    if metadata is None:
        return []
    timestamp, governorate, category = metadata
    matches = []
    for candidate in candidates:
        fields = candidate.fields
        other = grouping_metadata(candidate)
        if candidate.id == current.id or other is None or other[1:] != (governorate, category):
            continue
        other_time = other[0]
        delta = abs((other_time - timestamp).total_seconds())
        if delta <= WINDOW_SECONDS:
            matches.append(dict(id=candidate.id, state=candidate.state,
                                title_en=fields.get('title_en', ''), title_ar=fields.get('title_ar', ''),
                                occurred_at=other_time.isoformat().replace('+00:00', 'Z'),
                                private_governorate=governorate, time_difference_seconds=delta))
    return sorted(matches, key=lambda match: (match['time_difference_seconds'], match['id']))[:10]
