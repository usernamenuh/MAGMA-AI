from fastapi import APIRouter
from . import root, models, chat, embeddings, api_key

# Central router
router = APIRouter()

# Register sub-routers
router.include_router(root.router, tags=["root"])
router.include_router(models.router, tags=["models"])
router.include_router(chat.router, tags=["chat"])
router.include_router(embeddings.router, tags=["embeddings"])
router.include_router(api_key.router, tags=["api_keys"])