from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.brands import Brand as BrandModel
from app.schemas import Brand as BrandSchema, BrandCreate

from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db

# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/brands",
    tags=["brands"],
)


@router.get("/", response_model=list[BrandSchema])
async def get_all_brands(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список активных брендов.
    """
    result = await db.scalars(select(BrandModel).where(BrandModel.is_active==True))
    brands = result.all()
    return brands


@router.post("/", response_model=BrandSchema, status_code=status.HTTP_201_CREATED)
async def create_brand(brand: BrandCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Создаёт новый бренд.
    """
    db_brand = BrandModel(**brand.model_dump())
    db.add(db_brand)
    await db.commit()
    await db.refresh(db_brand)
    return db_brand



@router.put("/{brand_id}", response_model=BrandSchema)
async def update_brand(brand_id: int, brand: BrandCreate, db: AsyncSession = Depends(get_async_db)):
    """
    Обновляет бренд по его ID.
    """
    # Проверяем существование бренда
    stmt = select(BrandModel).where(BrandModel.id == brand_id,
                                       BrandModel.is_active == True)
    result = await db.scalars(stmt)
    db_brand = result.first()
    if not db_brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    # Обновляем категорию
    update_data = brand.model_dump(exclude_unset=True)
    await db.execute(
        update(BrandModel)
        .where(BrandModel.id == brand_id)
        .values(**update_data)
    )
    await db.commit()
    return db_brand


@router.delete("/{brand_id}", response_model=BrandSchema)
async def delete_brand(brand_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Выполняет мягкое удаление бренда по его ID, устанавливая is_active = False.
    """
    stmt = select(BrandModel).where(BrandModel.id == brand_id,
                                       BrandModel.is_active == True)
    result = await db.scalars(stmt)
    db_brand = result.first()
    if not db_brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")

    await db.execute(
        update(BrandModel)
        .where(BrandModel.id == brand_id)
        .values(is_active=False)
    )
    await db.commit()
    return db_brand
