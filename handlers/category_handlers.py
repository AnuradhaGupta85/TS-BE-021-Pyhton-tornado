# Category management endpoint handlers.
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import func, or_, select
import tornado.web

from base_handler import BaseHandler
from models import Category, Transaction
from schemas import CategoryCreateSchema, CategoryResponse

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


class CategoryCollectionHandler(BaseHandler):
    requires_auth = True

    async def get(self) -> None:
        limit, offset = self.pagination()
        where = or_(Category.is_predefined.is_(True), Category.owner_id == self.current_user.id)
        total = (await self.db.execute(select(func.count()).select_from(Category).where(where))).scalar_one()
        rows = (await self.db.execute(select(Category).where(where).order_by(Category.name).limit(limit).offset(offset))).scalars().all()
        self.write_json({'items': [CategoryResponse.model_validate(row).model_dump(mode='json') for row in rows], 'total': total, 'limit': limit, 'offset': offset})

    async def post(self) -> None:
        try:
            payload = CategoryCreateSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=self.validation_error_reason(exc)) from exc
        name = payload.name.strip()
        if not name:
            raise tornado.web.HTTPError(422, reason='Category name cannot be blank')
        exists = (await self.db.execute(select(Category).where(Category.name == name, Category.owner_id == self.current_user.id))).scalar_one_or_none()
        if exists:
            raise tornado.web.HTTPError(409, reason='Custom category already exists')
        category = Category(name=name, is_predefined=False, owner_id=self.current_user.id)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        self.write_json(CategoryResponse.model_validate(category).model_dump(mode='json'), 201)


class CategoryDetailHandler(BaseHandler):
    requires_auth = True

    async def delete(self, category_id: str) -> None:
        try:
            identifier = int(category_id)
        except ValueError as exc:
            raise tornado.web.HTTPError(404, reason='Category not found') from exc
        category = (await self.db.execute(select(Category).where(Category.id == identifier))).scalar_one_or_none()
        if category is None:
            raise tornado.web.HTTPError(404, reason='Category not found')
        if category.is_predefined or category.owner_id != self.current_user.id:
            raise tornado.web.HTTPError(403, reason='Only your unused custom categories can be deleted')
        in_use = (await self.db.execute(select(func.count()).select_from(Transaction).where(Transaction.category_id == category.id))).scalar_one()
        if in_use:
            raise tornado.web.HTTPError(409, reason='Category is in use by transactions')
        await self.db.delete(category)
        await self.db.commit()
        self.set_status(204)
        self.finish()
