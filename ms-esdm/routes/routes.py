from fastapi import APIRouter
from routes.v1 import analyze, logs, scrapping, api_keys, knowledge, authentication, chat_history, blobs

api_router = APIRouter()
api_router.include_router(authentication.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(analyze.router, prefix="/analyze", tags=["Analyze"])
api_router.include_router(logs.router, prefix="/logs", tags=["Logs"], include_in_schema=False)
api_router.include_router(scrapping.router, prefix="/scrapping", tags=["Scrapping"], include_in_schema=False)
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["API Keys"], include_in_schema=False)
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["Knowledge Documents"], include_in_schema=False)
api_router.include_router(chat_history.router, prefix="/chat", tags=["chat"], include_in_schema=False)
api_router.include_router(blobs.router, prefix="/blobs", tags=["blobs"], include_in_schema=False)
