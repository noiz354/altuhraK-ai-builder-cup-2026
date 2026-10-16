"""ASGI client avoiding cross-thread event-loop portals in restricted executors."""
import asyncio
import httpx


class LocalClient:
    def __init__(self, app):
        self.app = app

    def request(self, method, path, **kwargs):
        async def perform():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),
                                         base_url='http://testserver') as client:
                return await client.request(method, path, **kwargs)
        return asyncio.run(perform())

    def get(self, path, **kwargs): return self.request('GET', path, **kwargs)
    def post(self, path, **kwargs): return self.request('POST', path, **kwargs)
    def patch(self, path, **kwargs): return self.request('PATCH', path, **kwargs)
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): self.close()
