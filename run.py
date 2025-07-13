import uvicorn
from src.common.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
        loop=settings.app_loop,
    )
