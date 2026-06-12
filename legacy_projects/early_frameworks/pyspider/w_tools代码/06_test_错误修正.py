from bs4 import BeautifulSoup

# 原始HTML内容
html_content = '''  
<div class="product__additional-info--item t-text" id="description">
    <p>Designed for busy days out on the town, EVADER is waterproof all year round. Computer, bottle and more, this minimalist-looking backpack does indeed have maximumist capacity.</p><br>
<li>Waterproof fabric</li>
<li>Flap closure with buckle</li>
<li>1 zipped front pocket and 1 inside pocket</li>
<li>Custom strap 'JOTT</li>
<li>Reinforced, adjustable shoulder straps</li>
<li>Metal buckle detail on side</li>
<li>Tone-on-tone embossed rubber logo</li>
<li>Dimensions: 30 x 44 x 12 cm</li>
<p>Available in four colors: black, navy, fig and forest.</p><br>
  </div><div class="u-pad-t-xs u-pad-b-xs t-text">
  <span>Reference
    :
  </span>
  <span>FW24UBAC51</span>
  <span>-</span>
  <span>999</span>
</div><a href="https://jott.com/en-eu/pages/pictos-produits" class="product__properties u-marg-t-sm u-marg-b-sm | js-dataLayer-uxClick" target="_blank" data-uxclick-category="product" data-uxclick-sub-category="additional-info" data-uxclick-label="">


<div class="product__properties--item">
  <div class="product__properties--border">






<svg class="c-icon  c-icon--lg  ">
<use xlink:href="#icon-waterproof" x="0" y="0"></use>
</svg>


</div>
  <span class="t-text u-bold u-blue">Waterproof</span>
</div>

</a>
'''

# 使用BeautifulSoup解析HTML
soup = BeautifulSoup(html_content, 'html.parser')

# 找到ID为#description的div元素
description_div = soup.find('div', id='description')

# 如果找到了该div元素
if description_div:
    # 创建一个新的ul元素
    ul_element = soup.new_tag('ul', class_='ul_tab')

    # 找到div内的所有li元素，并将它们移动到新的ul元素中
    # 注意：这里使用decompose()的替代方案是extract()，它会移除元素但返回它，然后我们可以将其添加到ul中
    # 但是，由于我们想要在原地替换li元素，我们可以使用replace_with()结合wrap()的间接效果（但wrap已经足够）
    for li in description_div.find_all('li'):
        # 将li元素包裹在ul中（实际上是将li移动到ul中，并作为ul的子元素）
        li.wrap(ul_element)

# 打印修改后的HTML
print(soup.prettify())