import sys
import os

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time
import uvicorn

from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.responses import HTMLResponse, ORJSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

# from source.db.connect_db import init_db
from source.db.connect_db import get_session
from source.routes import routes_contacts, routes_auth, routes_users
from source.exceptions import exceptions
from source.services.redis_service import get_redis
# from fastapi.openapi.docs import get_swagger_ui_html


description = """

This FastAPI application provides a platform for users to manage their contacts data and user accounts. 
The application is divided into three main sections: Contacts, Auth, and Users.

## Contacts
This section provides endpoints for managing contact data. 
Users can create new contacts, search for existing contacts based on various criteria, 
update contact information, and delete contacts.

## Auth
This section contains endpoints for managing user accounts and authentication. 
Users can create a new account, log in to their account, refresh their access token when it expires, 
and log out of their account. This section also provides functionality for password management, 
including requesting a password reset email and resetting the password using a reset token.

## Users
This section provides endpoints for managing user profiles. 
Users can view their profile, update their avatar, and delete their profile.

The application also includes middleware for rate limiting and process time tracking, and it uses Redis for caching. 
It also includes a health checker endpoint for checking the database connection status.

The application is designed to be user-friendly and efficient, 
making it easy for users to manage their contacts and user accounts.

## Feedback

"""

fast_app = FastAPI(
    # debug=True,
    swagger_ui_parameters={"persistAuthorization": True},
    default_response_class=ORJSONResponse,
    title="FastApi application. Version: 2.6.1",
    description=description,
    contact={
        "name": "Wargoth",
        "url": "https://github.com/Wargoth-ks/FastApi.git",
        "email": "warheart1986@gmail.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://github.com/Wargoth-ks/FastApi/blob/main/LICENSE",
    },
)

# fast_app = FastAPI(docs_url=None)

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
STATIC_PATH = os.path.join(BASE_PATH, "front", "static")
TEMPLATES_PATH = os.path.join(BASE_PATH, "front", "templates")

fast_app.mount("/static", StaticFiles(directory=STATIC_PATH), name="static")

templates = Jinja2Templates(directory=TEMPLATES_PATH)


exceptions.register_exception_handlers(fast_app)


# @fast_app.get("/docs", include_in_schema=False)
# async def custom_swagger_ui_html():
#     return get_swagger_ui_html(
#         openapi_url=fast_app.openapi_url,
#         title="My API",
#         oauth2_redirect_url=fast_app.swagger_ui_oauth2_redirect_url,
#         swagger_js_url="/static/swagger-ui-bundle.js",  # Optional
#         swagger_css_url="/static/swagger-ui.css",  # Optional
#         swagger_favicon_url="/static/favicon-32x32.png",  # Optional
#     )


# origins = [ 
#     "http://localhost:3000"
#     ]

fast_app.add_middleware(
    CORSMiddleware, 
    allow_credentials=True,
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)


@fast_app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        async with get_redis() as redis:
            client = str(request.client.host)  # type: ignore
            current_minute = time.strftime("%Y-%m-%dT%H:%M")
            key = f"{client}_{current_minute}"
            count = await redis.get(key)

            if count is None:
                await redis.setex(key, 60, 1)  # ip, seconds, number of requests
            elif int(count) > 50:  # Set your desired rate limit here
                raise HTTPException(status_code=429, detail="Too many requests")
            else:
                await redis.incr(key)

            response = await call_next(request)
    except HTTPException as e:
        if request.url.path == "/" or request.url.path == "/docs":
            response = templates.TemplateResponse("429.html", {"request": request})
        else:
            response = ORJSONResponse(
                status_code=e.status_code, content={"detail": e.detail}
            )
    return response


@fast_app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["Process-Time"] = str(process_time)
    return response


@fast_app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@fast_app.get("/api/healthchecker", tags=["Check database status connection"])
async def healthchecker(db: AsyncSession = Depends(get_session)):
    try:
        stmt = await db.execute(select(text("1")))
        result = stmt.scalar()
        if result is None:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database is not configured correctly",
            )
        return {"message": "Database connection is ready"}
    except Exception as e:
        print(e)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error connecting to the database",
        )


fast_app.include_router(routes_auth.router, prefix="/api")
fast_app.include_router(routes_users.router, prefix="/api")
fast_app.include_router(routes_contacts.router, prefix="/api")


if __name__ == "__main__":
    uvicorn.run(
        "__main__:fast_app", host="0.0.0.0", port=8000, reload=True, log_level="debug"
    )
