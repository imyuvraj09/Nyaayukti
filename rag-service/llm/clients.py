"""Keep one SDK connection pool per worker thread; never share conversation state."""

import threading


class ThreadClients:
    def __init__(self):
        self._local = threading.local()
        self._clients = []
        self._lock = threading.Lock()

    def get(self, factory):
        client = getattr(self._local, "client", None)
        if client is None:
            client = factory()
            self._local.client = client
            with self._lock:
                self._clients.append(client)
        return client

    def close(self):
        # Called only after the server has drained its active requests.
        with self._lock:
            clients, self._clients = self._clients, []
        for client in clients:
            close = getattr(client, "close", None)
            if close:
                close()
