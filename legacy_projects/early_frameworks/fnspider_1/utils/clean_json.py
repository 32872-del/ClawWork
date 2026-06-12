import codecs
import json
import re


def clean_json(raw_str):
    if not raw_str or not isinstance(raw_str, str):
        return raw_str

    processed = raw_str.strip().strip('"').strip("'")

    processed = processed.replace('\\"', '"')

    processed = processed.replace('\\\\', '\\')  # 双斜杠变单斜杠

    unicode_regex = re.compile(r'\\u([0-9a-fA-F]{4})')

    def replace_unicode(match):
        return chr(int(match.group(1), 16))

    processed = unicode_regex.sub(replace_unicode, processed)

    # 5. 暴力尝试解析
    try:
        return json.loads(processed)
    except json.JSONDecodeError as e:
        try:
            return json.loads(processed.replace("'", '"'))
        except Exception:
            import ast
            return ast.literal_eval(processed)
