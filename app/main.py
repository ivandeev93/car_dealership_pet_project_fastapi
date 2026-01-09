from fastapi import FastAPI
from app.routers import brands, cars, users
from fastapi.staticfiles import StaticFiles

from app.routers import brands, cars, users


# Создаём приложение FastAPI
app = FastAPI(
    title="FastAPI Автосалон",
    version="0.1.0",
    summary="App for car dealership",
    contact={
    "name": "Иван Деев",
    "url": "https://example.com",
    "email": "deev-93-ivan@mail.ru"
}
)

# Подключение маршрутов
app.include_router(brands.router)
app.include_router(cars.router)
app.include_router(users.router)


# Для обслуживания медиа файлов
app.mount("/media", StaticFiles(directory="media"), name="media")
#Теперь любой файл из media/products/ будет доступен по URL: http://localhost:8000/media/products/abc123.jpg


# Корневой эндпоинт для проверки
@app.get("/")
async def root():
    """
    Корневой маршрут, подтверждающий, что API работает.
    """
    return {"message": "Добро пожаловать в API автосалона!"}
