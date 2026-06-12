from bs4 import BeautifulSoup


def remove_nodes_by_css(html_body):
    soup = BeautifulSoup(html_body or "", "html.parser")

    tags_to_remove = [
        "script", "style", "input", "iframe",
        "button", "path", "link", "meta", "noscript", "a",
    ]
    for tag_name in tags_to_remove:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    div_move_soup = soup.select_one("#_desktop_sizefit")
    if div_move_soup:
        div_move_soup.decompose()

    for strong_tag in soup.find_all("strong"):
        if strong_tag.get_text(strip=True) == "GWARANCJA na 12 miesięcy":
            strong_tag.decompose()

    attrs_to_keep = {"src", "alt", "width", "height", "id", "class", "href", "title"}

    for tag in soup.find_all():
        tag.attrs = {attr: tag[attr] for attr in list(tag.attrs.keys()) if attr in attrs_to_keep}

    for img in soup.find_all("img"):
        keep = {"src", "alt", "width", "height"}
        img.attrs = {k: v for k, v in img.attrs.items() if k in keep}

    for template in soup.find_all("template"):
        new_div = soup.new_tag("div")
        new_div.attrs = {k: v for k, v in template.attrs.items() if k in attrs_to_keep}
        new_div.extend(template.contents)
        template.replace_with(new_div)

    return str(soup)
