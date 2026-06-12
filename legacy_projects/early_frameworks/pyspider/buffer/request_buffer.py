from db.memorydb import MemoryDB
from utils.log import log

MAX_URL_COUNT = 1000


class AirSpiderRequestBuffer:
    def __init__(self, db=None):
        self._db = db or MemoryDB()

    def put_request(self, request, ignore_max_size=True):
        self._db.add(request, ignore_max_size=ignore_max_size)