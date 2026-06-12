from bs4 import BeautifulSoup

def remove_nodes_by_css(html_body):
    soup = BeautifulSoup(html_body, 'html.parser')

    # ====================== 1. 删除完全无用的标签 ======================
    tags_to_remove = [
        'script', 'style', 'input', 'iframe',
        'button', 'path', 'link', 'meta', 'noscript', 'a'
    ]
    for tag_name in tags_to_remove:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # #将a标签替换为span
    # for a_tag in soup.find_all('a'):
    #     new_tag = soup.new_tag('span')
    #     new_tag.string = a_tag.get_text()
    #     a_tag.replace_with(new_tag)


    # 删除指定文本的 strong 标签
    for strong_tag in soup.find_all('strong'):
        if strong_tag.get_text(strip=True) == "GWARANCJA na 12 miesięcy":
            strong_tag.decompose()

    # ====================== 2. 清理所有标签的无用属性 ======================
    attrs_to_keep = {
        'src', 'alt', 'width', 'height', 'id', 'class',
        'href', 'title'
    }

    for tag in soup.find_all():
        # 只保留需要的属性，其余全部删除
        new_attrs = {}
        for attr in list(tag.attrs.keys()):
            if attr in attrs_to_keep:
                new_attrs[attr] = tag[attr]
        tag.attrs = new_attrs

    # ====================== 3. 特殊清理 img 标签 ======================
    for img in soup.find_all('img'):
        # 保留必要属性，其他全部清空
        keep = ['src', 'alt', 'width', 'height']
        img.attrs = {k: v for k, v in img.attrs.items() if k in keep}

    # ====================== 4. template 替换为 div（保留内容） ======================
    for template in soup.find_all('template'):
        new_div = soup.new_tag('div')
        # 复制属性
        new_div.attrs = {k: v for k, v in template.attrs.items() if k in attrs_to_keep}
        # 复制内容
        if hasattr(template, 'content') and template.content:
            new_div.extend(template.content.contents)
        else:
            new_div.extend(template.contents)
        template.replace_with(new_div)

    # ====================== 5. 最终输出干净 HTML ======================
    clean_html = str(soup)
    return clean_html