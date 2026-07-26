import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from src.models.users import User
from src.routes.tasks import tasks_router
from src.routes.users import users_router

# Base.metadata.create_all(bind=engine) # Look at every model that inherits from Base, and create its table in the database if it doesn't already exist.

logger = logging.getLogger(__name__)
app = FastAPI()

app.include_router(tasks_router)
app.include_router(users_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "message": "Request failed",
            "detail": exc.detail
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "message": "Validation failed",
            "detail": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "message": "Internal server error",
            "detail": "Something went wrong"
        }
    )

@app.get("/")
async def root():
    return {"message": "Hello World"}
