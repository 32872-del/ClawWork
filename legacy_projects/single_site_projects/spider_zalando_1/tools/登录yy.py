import base64
import requests
import json
import ddddocr

ocr = ddddocr.DdddOcr(show_ad=False)
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9,cs;q=0.8,hu;q=0.7",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"147\", \"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"147\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "token": "",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
}
user_name = ""
password = ""

def get_code(ym):

    _url = f"https://{ym}/api/public/verify"
    _response = requests.get(_url, headers=headers).json()
    img = _response['data']['image'].split(",")[1]
    img_id = _response['data']['uniqid']
    code = ocr.classification(base64.b64decode(img))
    return code, img_id

def get_token(ym,code,img_id):
    url = f"https://{ym}/api/public/login"
    data = {
        "user_name": user_name,
        "password": password,
        "verify_code": "",
        "verify_key": "",
        "expire_seconds": 2592000,
        "img_code": code,
        "uniqid": img_id
    }
    data = json.dumps(data, separators=(',', ':'))
    response = requests.post(url, headers=headers, data=data).json()
    if response["msg"] == 'success':
        return response["data"]['token']
    else:
        return None

def get_products(ym):
    url = f"https://{ym}/api/products/base"
    params = {
        "pagesize": "50",
        "page": "1"
    }
    response = requests.get(url, headers=headers, params=params).json()
    all_name = response['data']['paginate']['total']
    page = all_name // 1000 +1
    return page

def main(ym):
    token = ''
    for _ in range(5):
        code,img_id = get_code(ym)
        token = get_token(ym,code,img_id)
        if token:
            break
        else:print('识别出错')
    headers['token'] = token
    page = get_products(ym)

if __name__ == '__main__':
    ym = 'rxea7ry8.abcshoppy.com'
    main(ym)