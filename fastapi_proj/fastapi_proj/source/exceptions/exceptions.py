from sqlalchemy.exc import IntegrityError, ProgrammingError, NoResultFound
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse
from fastapi import Request, status
from fastapi import FastAPI


def register_exception_handlers(fast_app: FastAPI):
    @fast_app.exception_handler(ValidationError)
    async def validation_pydantic_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({"Detail": str(exc).replace("\n", "").strip()}),
        )

    @fast_app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder({"Detail": exc.errors(), "Body": exc.body}),
        )

    @fast_app.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=jsonable_encoder(
                {"Detail": "Data already exists. Check input data, please"}
            ),
        )

    @fast_app.exception_handler(ProgrammingError)
    async def programming_exception_handler(request: Request, exc: ProgrammingError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(
                {"Detail": "Syntax error. Please, check input data."}
            ),
        )

    @fast_app.exception_handler(NoResultFound)
    async def no_result_exception_handler(request: Request, exc: NoResultFound):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=jsonable_encoder(
                {"Detail": "User not found."}
            ),
        )
    
    @fast_app.exception_handler(ResponseValidationError)
    async def validation_exception_handler_401(
        request: Request, exc: ResponseValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=jsonable_encoder(
                {"Detail: Unauthorised! Invalid email or password!"}
            ),
        )
