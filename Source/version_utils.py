def is_newer_version(latest_tag, current_version):
    try:
        latest_clean = latest_tag.lstrip('v').split('-')[0].split(' ')[0]
        current_clean = current_version.split('-')[0].split(' ')[0]
        latest_parts = [int(p) for p in latest_clean.split('.') if p.isdigit()]
        current_parts = [int(p) for p in current_clean.split('.') if p.isdigit()]
        return latest_parts > current_parts
    except Exception:
        return latest_tag != current_version
