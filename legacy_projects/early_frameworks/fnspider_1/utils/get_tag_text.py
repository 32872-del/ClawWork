from bs4 import BeautifulSoup, Comment




def get_tag_text(tag):

    texts = [
        t.strip()
        for t in tag.find_all(string=True, recursive=False)
        if t.strip() and not isinstance(t, Comment)
    ]

    return texts