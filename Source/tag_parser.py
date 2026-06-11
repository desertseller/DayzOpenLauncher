import re


def get_time_from_tags(tags):
    if not tags:
        return "?"
    match = re.search(r'([0-9]{2}:[0-9]{2})$', tags)
    if match:
        return match.group(1)
    match = re.search(r'(\d{1,2}:\d{2})', tags)
    if match:
        return match.group(1)
    return "?"


def get_queue_from_tags(tags):
    if not tags:
        return "0"
    tags = str(tags).lower()
    match = re.search(r'(?:lqs|lq|queue)[:\s]*(\d+)', tags)
    if match:
        return match.group(1)
    return "0"
