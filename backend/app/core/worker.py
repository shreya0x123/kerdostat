from uvicorn.workers import UvicornWorker

class CustomUvicornWorker(UvicornWorker):
    CONFIG_KWARGS = {"ws": "wsproto", "loop": "auto"}
