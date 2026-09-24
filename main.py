# Tornado application entry point and route configuration.
import asyncio
import os

from dotenv import load_dotenv
import tornado.ioloop
import tornado.web

from base_handler import BaseHandler
from handlers.auth_handlers import (ChangePasswordHandler, ForgotPasswordHandler,
                                    LoginHandler, LogoutHandler, MeHandler,
                                    RegisterHandler, ResetPasswordHandler)
from handlers.category_handlers import CategoryCollectionHandler, CategoryDetailHandler
from handlers.transaction_handlers import (MonthlySummaryHandler, TagCollectionHandler,
                                           TagDetailHandler, TransactionAttachmentHandler,
                                           TransactionBulkHandler, TransactionCollectionHandler,
                                           TransactionDetailHandler)
from seed import seed

load_dotenv('.env_10c6229a-2c2d-44bf-a722-7f4465657ae8', override=True)


class HealthHandler(BaseHandler):
    async def get(self) -> None:
        self.write_json({'status': 'ok'})


def make_app() -> tornado.web.Application:
    return tornado.web.Application([
        tornado.web.URLSpec(r'/health', HealthHandler),
        tornado.web.URLSpec(r'/api/v1/auth/register', RegisterHandler),
        tornado.web.URLSpec(r'/api/v1/auth/login', LoginHandler),
        tornado.web.URLSpec(r'/api/v1/auth/me', MeHandler),
        tornado.web.URLSpec(r'/api/v1/auth/change-password', ChangePasswordHandler),
        tornado.web.URLSpec(r'/api/v1/auth/forgot-password', ForgotPasswordHandler),
        tornado.web.URLSpec(r'/api/v1/auth/reset-password', ResetPasswordHandler),
        tornado.web.URLSpec(r'/api/v1/auth/logout', LogoutHandler),
        tornado.web.URLSpec(r'/api/v1/categories', CategoryCollectionHandler),
        tornado.web.URLSpec(r'/api/v1/categories/([^/]+)', CategoryDetailHandler),
        tornado.web.URLSpec(r'/api/v1/transactions/bulk', TransactionBulkHandler),
        tornado.web.URLSpec(r'/api/v1/transactions/([^/]+)/attachment', TransactionAttachmentHandler),
        tornado.web.URLSpec(r'/api/v1/transactions', TransactionCollectionHandler),
        tornado.web.URLSpec(r'/api/v1/transactions/([^/]+)', TransactionDetailHandler),
        tornado.web.URLSpec(r'/api/v1/tags', TagCollectionHandler),
        tornado.web.URLSpec(r'/api/v1/tags/([^/]+)', TagDetailHandler),
        tornado.web.URLSpec(r'/api/v1/summary/monthly', MonthlySummaryHandler),
    ], debug=False)


if __name__ == '__main__':
    asyncio.run(seed())
    port = int(os.getenv('PORT', '21435'))
    make_app().listen(port)
    tornado.ioloop.IOLoop.current().start()
