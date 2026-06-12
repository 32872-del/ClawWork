import json
import re


def clean_json(raw_str):
    if not raw_str or not isinstance(raw_str, str):
        return raw_str

    processed = raw_str.strip().strip('"').strip("'")
    processed = processed.replace('\\"', '"')
    processed = processed.replace('\\\\', '\\')

    unicode_regex = re.compile(r'\\u([0-9a-fA-F]{4})')
    processed = unicode_regex.sub(lambda match: chr(int(match.group(1), 16)), processed)

    try:
        return json.loads(processed)
    except json.JSONDecodeError:
        try:
            return json.loads(processed.replace("'", '"'))
        except Exception:
            import ast
            return ast.literal_eval(processed)
