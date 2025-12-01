"""WSGI entry point for production deployment"""
from app import asgi_app

# For ASGI servers like gunicorn with uvicorn workers
application = asgi_app

if __name__ == "__main__":
    import uvicorn
    from config import Config
    
    uvicorn.run(
        "wsgi:application",
        host=Config.HOST,
        port=Config.PORT,
        log_level="info",
    )





