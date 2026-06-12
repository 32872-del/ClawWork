from bs4 import Comment


def get_tag_text(tag):
    return [
        text.strip()
        for text in tag.find_all(string=True, recursive=False)
        if text.strip() and not isinstance(text, Comment)
    ]
