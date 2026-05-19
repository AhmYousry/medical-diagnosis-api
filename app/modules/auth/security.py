from passlib.context import CryptContext
from starlette.concurrency import run_in_threadpool

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


async def hash_password_async(password: str) -> str:
    return await run_in_threadpool(hash_password, password)


async def verify_password_async(plain_password: str, password_hash: str) -> bool:
    return await run_in_threadpool(verify_password, plain_password, password_hash)
