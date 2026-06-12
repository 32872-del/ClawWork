import hashlib


def hash_md5(value):
    """
    将数据加密为 md5 值，方便存储和查询
    """
    m = hashlib.md5()
    m.update(value.encode())
    return m.hexdigest()


if __name__ == '__main__':
    print(hash_md5('_client_type=20back=0fr=kz=8967931093last_pid=150063716761lz=0mark_type=0r=0session_request_times=3subapp_type=pctbs=64d2138606a1025c178030695036770b1f34c9bbf2e7d1a99d2b82fa9e'))