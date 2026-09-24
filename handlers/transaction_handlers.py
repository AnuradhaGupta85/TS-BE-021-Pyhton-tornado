# Transaction CRUD, filtering, sorting, and monthly summary handlers.
from datetime import date
from decimal import Decimal

from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
import tornado.web

from base_handler import BaseHandler
from models import Category, Transaction, TransactionType
from schemas import TransactionCreateSchema, TransactionResponse, TransactionUpdateSchema

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


def transaction_data(row: Transaction) -> dict:
    return TransactionResponse(id=row.id, amount=row.amount, type=row.type, category_id=row.category_id, category_name=row.category.name, date=row.date, description=row.description, user_id=row.user_id).model_dump(mode='json')


async def accessible_category(handler: BaseHandler, category_id: int) -> Category:
    category = (await handler.db.execute(select(Category).where(Category.id == category_id))).scalar_one_or_none()
    if category is None or (not category.is_predefined and category.owner_id != handler.current_user.id):
        raise tornado.web.HTTPError(422, reason='Category is unavailable')
    return category


class TransactionCollectionHandler(BaseHandler):
    requires_auth = True

    async def get(self) -> None:
        limit, offset = self.pagination()
        conditions = [Transaction.user_id == self.current_user.id]
        search = self.get_query_argument('search', '').strip()
        if search:
            conditions.append(or_(Transaction.description.ilike(f'%{search}%'), Category.name.ilike(f'%{search}%')))
        type_value = self.get_query_argument('type', '').strip()
        if type_value:
            try:
                conditions.append(Transaction.type == TransactionType(type_value))
            except ValueError as exc:
                raise tornado.web.HTTPError(400, reason='type must be Income or Expense') from exc
        for param, column, label in [('start_date', Transaction.date, 'start_date'), ('end_date', Transaction.date, 'end_date')]:
            raw = self.get_query_argument(param, '').strip()
            if raw:
                try:
                    parsed = date.fromisoformat(raw)
                except ValueError as exc:
                    raise tornado.web.HTTPError(400, reason=f'{label} must be YYYY-MM-DD') from exc
                conditions.append(column >= parsed if param == 'start_date' else column <= parsed)
        category_id = self.get_query_argument('category_id', '').strip()
        if category_id:
            try:
                conditions.append(Transaction.category_id == int(category_id))
            except ValueError as exc:
                raise tornado.web.HTTPError(400, reason='category_id must be an integer') from exc
        sort_by = self.get_query_argument('sort_by', 'date')
        sort_fields = {'date': Transaction.date, 'amount': Transaction.amount, 'category': Category.name}
        if sort_by not in sort_fields:
            raise tornado.web.HTTPError(400, reason='sort_by must be date, amount, or category')
        order = self.get_query_argument('order', 'desc').lower()
        if order not in {'asc', 'desc'}:
            raise tornado.web.HTTPError(400, reason='order must be asc or desc')
        total = (await self.db.execute(select(func.count()).select_from(Transaction).join(Category).where(*conditions))).scalar_one()
        ordering = sort_fields[sort_by].asc() if order == 'asc' else sort_fields[sort_by].desc()
        rows = (await self.db.execute(select(Transaction).join(Transaction.category).options(selectinload(Transaction.category)).where(*conditions).order_by(ordering, Transaction.id.desc()).limit(limit).offset(offset))).scalars().all()
        self.write_json({'items': [transaction_data(row) for row in rows], 'total': total, 'limit': limit, 'offset': offset})

    async def post(self) -> None:
        try:
            payload = TransactionCreateSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=str(exc)) from exc
        await accessible_category(self, payload.category_id)
        row = Transaction(amount=payload.amount, type=payload.type, category_id=payload.category_id, date=payload.date, description=payload.description, user_id=self.current_user.id)
        self.db.add(row)
        await self.db.commit()
        result = await self.db.execute(select(Transaction).options(selectinload(Transaction.category)).where(Transaction.id == row.id))
        row = result.scalar_one()
        self.write_json(transaction_data(row), 201)


class TransactionDetailHandler(BaseHandler):
    requires_auth = True

    async def _row(self, transaction_id: str) -> Transaction:
        try:
            identifier = int(transaction_id)
        except ValueError as exc:
            raise tornado.web.HTTPError(404, reason='Transaction not found') from exc
        row = (await self.db.execute(select(Transaction).options(selectinload(Transaction.category)).where(Transaction.id == identifier, Transaction.user_id == self.current_user.id))).scalar_one_or_none()
        if row is None:
            raise tornado.web.HTTPError(404, reason='Transaction not found')
        return row

    async def get(self, transaction_id: str) -> None:
        self.write_json(transaction_data(await self._row(transaction_id)))

    async def put(self, transaction_id: str) -> None:
        row = await self._row(transaction_id)
        try:
            payload = TransactionUpdateSchema.model_validate(self.json_body())
        except ValidationError as exc:
            raise tornado.web.HTTPError(422, reason=str(exc)) from exc
        values = payload.model_dump(exclude_unset=True)
        if 'category_id' in values:
            await accessible_category(self, values['category_id'])
        for field, value in values.items():
            setattr(row, field, value)
        await self.db.commit()
        result = await self.db.execute(select(Transaction).options(selectinload(Transaction.category)).where(Transaction.id == row.id))
        self.write_json(transaction_data(result.scalar_one()))

    async def delete(self, transaction_id: str) -> None:
        row = await self._row(transaction_id)
        await self.db.delete(row)
        await self.db.commit()
        self.set_status(204)
        self.finish()


class MonthlySummaryHandler(BaseHandler):
    requires_auth = True

    async def get(self) -> None:
        try:
            year = int(self.get_query_argument('year'))
            month = int(self.get_query_argument('month'))
            period_start = date(year, month, 1)
        except (tornado.web.MissingArgumentError, ValueError) as exc:
            raise tornado.web.HTTPError(400, reason='year and month must form a valid month') from exc
        period_end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
        base = [Transaction.user_id == self.current_user.id, Transaction.date >= period_start, Transaction.date < period_end]
        totals = (await self.db.execute(select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0)).where(*base).group_by(Transaction.type))).all()
        by_type = {kind: Decimal(str(value)) for kind, value in totals}
        breakdown = (await self.db.execute(select(Category.name, func.sum(Transaction.amount)).join(Transaction).where(*base, Transaction.type == TransactionType.EXPENSE).group_by(Category.id, Category.name).order_by(Category.name))).all()
        income = by_type.get(TransactionType.INCOME, Decimal('0'))
        expense = by_type.get(TransactionType.EXPENSE, Decimal('0'))
        self.write_json({'total_income': income, 'total_expenses': expense, 'balance': income - expense, 'expenses_by_category': [{'category': name, 'total': total} for name, total in breakdown]})
