def deep_fun(payload_dict: dict, func=None) -> list:
    result_list = []

    def req(data: dict, item: dict = None, deep=1):
        if item is None:
            item = {}

        dict_title = f"categories_{deep}"

        for k, v in data.items():
            k = str(k).strip()

            new_item = item.copy()
            new_item[dict_title] = k
            new_item["page_nums"] = 1

            if isinstance(v, dict):
                req(v, new_item, deep=deep + 1)
            else:
                url = func(v) if func else v
                if not url:
                    continue
                new_item["url"] = url
                result_list.append(new_item)

    req(payload_dict)
    return result_list
