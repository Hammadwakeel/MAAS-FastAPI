"""
Server runner script for the PageSpeed Insights API.
"""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"🚀 Starting {settings.app_name}")
    print(f"📍 Server: {settings.host}:{settings.port}")
    print(f"🔧 Debug Mode: {settings.debug}")
    print(f"📚 API Documentation: http://{settings.host}:{settings.port}/docs")
    print(f"📋 Alternative Docs: http://{settings.host}:{settings.port}/redoc")
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )