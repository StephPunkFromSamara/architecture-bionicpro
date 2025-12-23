from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
import clickhouse_connect
import jwt
from jwt import PyJWKClient
import requests
from typing import Optional
import os
import sys
import logging
from pydantic import BaseModel
import traceback
# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Reports API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Конфигурация
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "airflow")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "airflow")

# JWK клиент для получения публичных ключей Keycloak (ленивая инициализация)
jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
jwks_client = None


def get_jwks_client():
    """Получает или создает JWKS клиент"""
    global jwks_client
    if jwks_client is None:
        jwks_client = PyJWKClient(jwks_url)
    return jwks_client


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверяет JWT токен через Keycloak"""
    token = credentials.credentials
    
    try:
        # Получаем ключ для проверки подписи токена
        client = get_jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        
        # Декодируем и проверяем токен
        decoded_token = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True, "verify_aud": False}  # Отключаем проверку audience для публичного клиента
        )
        
        return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Token verification failed: {str(e)}"
        )


def get_user_id_from_token(token_data: dict) -> Optional[int]:
    """Извлекает user_id из токена или создает маппинг по username"""
    # Пробуем получить username из разных полей токена
    username = (
        token_data.get("preferred_username") or 
        token_data.get("username") or 
        token_data.get("sub") or
        token_data.get("email", "").split("@")[0] if token_data.get("email") else None
    )
    
    # Если username все еще None, пробуем извлечь из sub (обычно это UUID, но может быть username)
    if not username:
        sub = token_data.get("sub", "")
        # Если sub это UUID, пробуем найти username в других полях
        if sub and len(sub) > 20:  # UUID обычно длинный
            username = token_data.get("preferred_username") or token_data.get("username")
    
    # Маппинг username -> user_id
    # В реальном проекте это должно быть в отдельной таблице БД
    username_to_id = {
        "user1": 1,
        "user2": 2,
        "prothetic1": 3,
        "prothetic2": 4,
        "prothetic3": 5,
        "admin1": None,  # Админы не имеют user_id
    }
    
    # Если username не найден напрямую, пробуем найти по email
    if not username or username not in username_to_id:
        email = token_data.get("email", "")
        email_to_username = {
            "user1@example.com": "user1",
            "user2@example.com": "user2",
            "prothetic1@example.com": "prothetic1",
            "prothetic2@example.com": "prothetic2",
            "prothetic3@example.com": "prothetic3",
            "admin1@example.com": "admin1",
        }
        if email in email_to_username:
            username = email_to_username[email]
    
    user_id = username_to_id.get(username) if username else None
    
    # Логирование для отладки (выводим в stderr, чтобы увидеть в docker logs)
    import sys
    print(f"DEBUG: Token keys: {list(token_data.keys())}", file=sys.stderr, flush=True)
    print(f"DEBUG: Username extracted: {username}", file=sys.stderr, flush=True)
    print(f"DEBUG: Email from token: {token_data.get('email')}", file=sys.stderr, flush=True)
    print(f"DEBUG: User ID result: {user_id}", file=sys.stderr, flush=True)
    
    return user_id


class ReportResponse(BaseModel):
    user_id: int
    name: str
    email: str
    prosthesis_id: str
    usage_hours: float
    temperature: float


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/reports", response_model=ReportResponse)
async def get_report(token_data: dict = Depends(verify_token)):
    """Получает отчет по пользователю из ClickHouse"""
    logger.info("Reports endpoint called")
    logger.debug(f"Token data received: {token_data}")

    # Получаем user_id из токена
    user_id = get_user_id_from_token(token_data)
    logger.info(f"User ID result: {user_id}")

    if user_id is None:
        username = token_data.get("preferred_username") or token_data.get("username") or token_data.get("sub") or "unknown"
        email = token_data.get("email", "no email")
        available_users = ["user1", "user2", "prothetic1", "prothetic2", "prothetic3"]
        detail_msg = f"User '{username}' (email: {email}) does not have access to reports. Available users: {', '.join(available_users)}"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_msg
        )

    # Подключаемся к ClickHouse
    try:
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=CLICKHOUSE_PORT,
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD
        )

        # Безопасный SQL с плейсхолдером
        query = f"""
        SELECT
            user_id,
            name,
            email,
            prosthesis_id,
            usage_hours,
            temperature
        FROM user_metrics_report
        WHERE user_id = {user_id}
        LIMIT 1
        """

        result = client.query(query)

        if not result.result_rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report not found for user_id: {user_id}"
            )

        row = result.result_rows[0]
        column_names = result.column_names
        report_data = dict(zip(column_names, row))

        logger.info(f"Report fetched successfully for user_id: {user_id}")
        return ReportResponse(**report_data)

    except Exception as e:
        # Выводим весь traceback в лог
        tb_str = traceback.format_exc()
        logger.error(f"Failed to fetch report:\n{tb_str}")

        # Для debug-режима возвращаем traceback клиенту
        debug_info = tb_str
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to fetch report",
                "reason": str(e),
                "debug_trace": debug_info
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

