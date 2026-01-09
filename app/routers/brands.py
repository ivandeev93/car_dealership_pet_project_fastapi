from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.brands import Brand as BrandModel
from app.schemas import Category as CategorySchema, CategoryCreate
from app.db_depends import get_db

from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db

# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/brands",
    tags=["brands"],
)


@router.get("/")
async def get_all_brands():
    """
    Возвращает список всех марок.
    """
    return {"message": "Список всех категорий (заглушка)"}


@router.post("/")
async def create_brand():
    """
    Создаёт новую марку
    """
    return {"message": "Категория создана (заглушка)"}


@router.put("/{brand_id}")
async def update_brand(brand_id: int):
    """
    Обновляет категорию по её ID.
    """
    return {"message": f"Категория с ID {brand_id} обновлена (заглушка)"}


@router.delete("/{brand_id}")
async def delete_brand(brand_id: int):
    """
    Удаляет категорию по её ID.
    """
    return {"message": f"Категория с ID {brand_id} удалена (заглушка)"}