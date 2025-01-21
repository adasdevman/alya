import aiohttp


class AuthClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    async def authenticate(self, service, username, password, ssl=True):
        if ssl:
            http_mode = "https"
        else:
            http_mode = "http"
        url = f"{http_mode}://{self.host}:{self.port}/{service}/authenticate/"
        payload = {"username": username, "password": password}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    return True
                return False
