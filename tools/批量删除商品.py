import argparse
import base64
import getpass
import json

import requests


HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-CN,zh;q=0.9",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome Safari/537.36",
}


def get_code(domain, headers, ocr):
    response = requests.get(f"https://{domain}/api/public/verify", headers=headers, timeout=30).json()
    img = response["data"]["image"].split(",", 1)[1]
    img_id = response["data"]["uniqid"]
    code = ocr.classification(base64.b64decode(img))
    return code, img_id


def get_token(domain, user_name, password, code, img_id, headers):
    data = {
        "user_name": user_name,
        "password": password,
        "verify_code": "",
        "verify_key": "",
        "expire_seconds": 2592000,
        "img_code": code,
        "uniqid": img_id,
    }
    response = requests.post(
        f"https://{domain}/api/public/login",
        headers=headers,
        data=json.dumps(data, separators=(",", ":")),
        timeout=30,
    ).json()
    if response.get("msg") == "success":
        return response["data"]["token"]
    return None


def get_page_count(domain, headers, page_size):
    response = requests.get(
        f"https://{domain}/api/products/base",
        headers=headers,
        params={"pagesize": str(page_size), "page": "1"},
        timeout=30,
    ).json()
    total = response["data"]["paginate"]["total"]
    return total // page_size + (1 if total % page_size else 0), total


def delete_products(domain, headers, page_count, page_size):
    for _ in range(page_count):
        response = requests.get(
            f"https://{domain}/api/products/base",
            headers=headers,
            params={"pagesize": str(page_size), "page": "1"},
            timeout=30,
        ).json()
        ids = [item["id"] for item in response["data"]["list"]]
        if not ids:
            break

        response = requests.post(
            f"https://{domain}/api/products/batchdelete",
            headers=headers,
            data=json.dumps({"ids": ids}, separators=(",", ":")),
            timeout=30,
        ).json()
        print(response.get("msg", response))


def login(domain, user_name, password, headers):
    try:
        import ddddocr
    except ImportError as exc:
        raise RuntimeError("缺少 ddddocr，请先安装后再执行删除操作。") from exc

    ocr = ddddocr.DdddOcr(show_ad=False)
    for _ in range(5):
        code, img_id = get_code(domain, headers, ocr)
        token = get_token(domain, user_name, password, code, img_id, headers)
        if token:
            return token
        print("验证码识别失败，重试中...")
    raise RuntimeError("登录失败，请检查账号、密码或验证码接口")


def main():
    parser = argparse.ArgumentParser(description="批量删除后台商品，需要显式确认")
    parser.add_argument("domain", help="后台域名，不要带 https://")
    parser.add_argument("--user", required=True, help="登录账号")
    parser.add_argument("--password", help="登录密码；不传则交互输入")
    parser.add_argument("--page-size", type=int, default=1000, help="每次删除数量，默认 1000")
    parser.add_argument("--yes", action="store_true", help="确认执行删除")
    args = parser.parse_args()

    if not args.yes:
        raise SystemExit("这是删除操作，请加 --yes 确认执行。")

    password = args.password or getpass.getpass("Password: ")
    headers = dict(HEADERS)
    headers["token"] = login(args.domain, args.user, password, headers)

    page_count, total = get_page_count(args.domain, headers, args.page_size)
    print(f"准备删除 {total} 个商品，预计 {page_count} 批。")
    delete_products(args.domain, headers, page_count, args.page_size)


if __name__ == "__main__":
    main()
