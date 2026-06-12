from queue import PriorityQueue

import setting


class MemoryDB:
    def __init__(self):
        self.priority_queue = PriorityQueue(maxsize=setting.TASK_MAX_CACHED_SIZE)
    def add(self, item, ignore_max_size=False):
        if ignore_max_size:
            self.priority_queue._put(item)
            self.priority_queue.unfinished_tasks += 1
        else:
            self.priority_queue.put(item)
    def get(self):
        try:
            item = self.priority_queue.get(timeout=1)
            return item
        except:
            return
    def empty(self):
        return self.priority_queue.empty()
