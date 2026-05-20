import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid
from datetime import datetime
from models.chat_histories import ChatHistory
from models.dto.chat_history_dto import ChatHistoryDTO


class ChatHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def map_to_dto(self, entity: ChatHistory) -> ChatHistoryDTO:
        raw_type = entity.type or 'api_docs-id'

        if '-' in raw_type:
            doc_type, lang = raw_type.split('-', 1)
        else:
            doc_type = raw_type
            lang = 'id'

        return ChatHistoryDTO(
            chat_id=entity.chat_id,
            user_id=entity.user_id,
            session_id=entity.session_id,
            role=entity.role,
            type=doc_type or 'api_docs',
            lang=lang or 'id',
            message=entity.message,
            api_call=entity.api_call,
            geo_location=entity.geo_location,
            references=entity.references,
            response=entity.response,
            created_at=entity.created_at,
        )

    def map_list_to_dto(self, entities: list[ChatHistory]) -> list[ChatHistoryDTO]:
        return [self.map_to_dto(e) for e in entities]


    async def create_message(self, user_id: str, session_id: str, role: str, message: str, api_call: str = None, response=None, type: str = 'api_docs', references =None, lang='id', geo_location=None):
        chat = ChatHistory(
            chat_id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            role=role,
            message=message,
            api_call=api_call,
            response=response,
            references=references,
            type=type+'-'+lang,
            geo_location=geo_location,
            created_at=datetime.utcnow()
        )

        self.db.add(chat)
        await self.db.commit()
        await self.db.refresh(chat)
        return chat

    async def get_session_messages(self, user_id: str, session_id: str, limit: int = 100):
        stmt = (
            select(ChatHistory)
            .where(
                ChatHistory.user_id == user_id,
                ChatHistory.session_id == session_id
            )
            .order_by(ChatHistory.created_at)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        entities = result.scalars().all()

        return self.map_list_to_dto(entities)

    async def get_user_sessions(self, user_id: str, limit: int = 20):
        # Subquery: latest message per session
        subq = (
            select(
                ChatHistory.session_id,
                ChatHistory.created_at
            )
            .where(ChatHistory.user_id == user_id)
            .order_by(ChatHistory.session_id, ChatHistory.created_at.desc())
            .distinct(ChatHistory.session_id)
            .limit(limit)
            .subquery()
        )

        stmt = (
            select(ChatHistory)
            .join(
                subq,
                (ChatHistory.session_id == subq.c.session_id)
                & (ChatHistory.created_at == subq.c.created_at)
            )
            .order_by(subq.c.created_at.desc())
        )

        result = await self.db.execute(stmt)
        entities = result.scalars().all()
        return self.map_list_to_dto(entities)

    async def delete_session(self, session_id: str):
        stmt = delete(ChatHistory).where(ChatHistory.session_id == session_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete_user_history(self, user_id: str):
        stmt = delete(ChatHistory).where(ChatHistory.user_id == user_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
