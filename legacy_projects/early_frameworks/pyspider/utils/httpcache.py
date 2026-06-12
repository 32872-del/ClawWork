import gzip
import json
import logging
import os
import pickle
from network.request import Request
from network.response import Response
from utils.tools import to_bytes
from time import time
import setting

logger = logging.getLogger(__name__)


class FilesystemCacheStorage:

    def __init__(self):
        self.cachedir = setting.HTTPCACHE_DIR
        self.expiration_secs = setting.HTTPCACHE_EXPIRATION_SECS

    def retrieve_response(self, request: Request):
        """Return response if present in cache, or None otherwise."""
        metadata = self._read_meta(request)
        if metadata is None:
            return  # not cached
        rpath = self._get_request_path(request)
        with open(os.path.join(rpath, 'response_dict'), 'rb') as f:
            resp = f.read()

        response = Response.from_dict(json.loads(resp))
        return response

    def store_response(self, request: Request, response: Response):
        """Store the given response in the cache."""
        rpath = self._get_request_path(request)
        if not os.path.exists(rpath):
            os.makedirs(rpath)
        metadata = {
            'url': request.url,
            'method': request.method,
            'status': response.status_code,
            'response_url': response.url,
            'timestamp': time(),
        }
        with open(os.path.join(rpath, 'meta'), 'wb') as f:
            f.write(to_bytes(repr(metadata)))
        with open(os.path.join(rpath, 'pickled_meta'), 'wb') as f:
            pickle.dump(metadata, f, protocol=4)
        with open(os.path.join(rpath, 'request_dict'), 'wb') as f:
            f.write(request.to_dict())
        with open(os.path.join(rpath, 'response_dict'), 'wb') as f:
            f.write(request.to_dict())

    def _get_request_path(self, request):
        key = request.fingerprint
        return os.path.join(self.cachedir, request.parser_name, key[0:2], key)

    def _read_meta(self, request: Request):
        rpath = self._get_request_path(request)
        metapath = os.path.join(rpath, 'pickled_meta')
        if not os.path.exists(metapath):
            return  # not found
        mtime = os.stat(metapath).st_mtime
        if 0 < self.expiration_secs < time() - mtime:
            return  # expired
        with open(metapath, 'rb') as f:
            return pickle.load(f)
