from pathlib import Path
import uuid
from fastapi import UploadFile, File, Form

from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy import select, update, func, desc

from app.models.cars import Car as CarModel
from app.schemas import Car as CarSchema, CarCreate, CarList
from app.models.brands import Brand as BrandModel

from app.models.users import User as UserModel
from app.auth import get_current_admin                   # auth

from sqlalchemy.ext.asyncio import AsyncSession

from app.db_depends import get_async_db


BASE_DIR = Path(__file__).resolve().parent.parent.parent     # Абсолютный путь к корню проекта
MEDIA_ROOT = BASE_DIR / "media" / "cars"        # Физическая папка на диске, куда сохраняются изображения товаров
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)                 # Создаёт папку, если её нет
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}   # Допустимые разрешения изображений
MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2 097 152 байт


async def save_car_image(file: UploadFile) -> str:
    """
    Сохраняет изображение авто и возвращает относительный URL.
    """
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only JPG, PNG or WebP images are allowed")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image is too large")

    extension = Path(file.filename or "").suffix.lower() or ".jpg"
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = MEDIA_ROOT / file_name
    file_path.write_bytes(content)

    return f"/media/cars/{file_name}"


def remove_car_image(url: str | None) -> None:
    """
    Удаляет файл изображения, если он существует.
    """
    if not url:
        return
    relative_path = url.lstrip("/")
    file_path = BASE_DIR / relative_path
    if file_path.exists():
        file_path.unlink()


# Создаём маршрутизатор с префиксом и тегом
router = APIRouter(
    prefix="/cars",
    tags=["cars"],
)


@router.get("/", response_model=CarList)
async def get_all_cars(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    brand_id: int | None = Query(None, description="ID бренда для фильтрации"),
    search: str | None = Query(None, min_length=1, description="Поиск по названию/описанию"),
    min_price: float | None = Query(None, ge=0, description="Минимальная цена автомобиля"),
    max_price: float | None = Query(None, ge=0, description="Максимальная цена автомобиля"),
    in_stock: bool | None = Query(None, description="true — только авто в наличии, false — только без остатка"),
    db: AsyncSession = Depends(get_async_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_price не может быть больше max_price",
        )

    filters = [CarModel.is_active.is_(True)]

    if brand_id is not None:
        filters.append(CarModel.brand_id == brand_id)
    if min_price is not None:
        filters.append(CarModel.price >= min_price)
    if max_price is not None:
        filters.append(CarModel.price <= max_price)
    if in_stock is not None:
        filters.append(CarModel.stock > 0 if in_stock else CarModel.stock == 0)

    # Базовый запрос total
    total_stmt = select(func.count()).select_from(CarModel).where(*filters)

    # Поиск по названию/описанию
    rank_col = None
    if search:
        search_value = search.strip()
        if search_value:
            ts_query = func.websearch_to_tsquery('english', search_value)
            filters.append(CarModel.tsv.op('@@')(ts_query))
            rank_col = func.ts_rank_cd(CarModel.tsv, ts_query).label("rank")
            # total с учётом полнотекстового фильтра
            total_stmt = select(func.count()).select_from(CarModel).where(*filters)

    total = await db.scalar(total_stmt) or 0

    # Основной запрос (если есть поиск — добавим ранг в выборку и сортировку)
    if rank_col is not None:
        cars_stmt = (
            select(CarModel, rank_col)
            .where(*filters)
            .order_by(desc(rank_col), CarModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(cars_stmt)
        rows = result.all()
        items = [row[0] for row in rows]

    else:
        cars_stmt = (
            select(CarModel)
            .where(*filters)
            .order_by(CarModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await db.scalars(cars_stmt)).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/brand/{brand_id}", response_model=list[CarSchema])
async def get_cars_by_brand(brand_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список активных авто по ID бренда.
    """
    # Проверяем, существует ли активная категория
    result = await db.scalars(
        select(BrandModel).where(BrandModel.id == brand_id,
                                    BrandModel.is_active == True)
    )
    brand = result.first()
    if not brand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Brand not found or inactive")

    # Получаем активные товары в категории
    car_result = await db.scalars(
        select(CarModel).where(CarModel.brand_id == brand_id,
                                   CarModel.is_active == True)
    )
    cars = car_result.all()
    return cars


@router.get("/{car_id}", response_model=CarSchema)
async def get_car(car_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию об автомобиле по его ID.
    """
    # Проверяем, существует ли активный товар
    car_result = await db.scalars(
        select(CarModel).where(CarModel.id == car_id, CarModel.is_active == True)
    )
    car = car_result.first()
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found or inactive")

    # Проверяем, существует ли активный бренд
    brand_result = await db.scalars(
        select(BrandModel).where(BrandModel.id == car.brand_id,
                                    BrandModel.is_active == True)
    )
    brand = brand_result.first()
    if not brand:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Brand not found or inactive")

    return car


@router.post("/", response_model=CarSchema, status_code=status.HTTP_201_CREATED)
async def create_car(
        car: CarCreate = Depends(CarCreate.as_form),
        image: UploadFile | None = File(None),
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_admin)          ########### auth
):
    """
    Создаёт новый авто, привязанный к текущему салону (только для 'admin').
    """

    brand_result = await db.scalars(
        select(BrandModel).where(BrandModel.id == car.brand_id,
                                    BrandModel.is_active == True)
    )
    if not brand_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Brand not found or inactive")

    # Сохранение изображения (если есть)
    image_url = await save_car_image(image) if image else None

    # Создание товара
    db_car = CarModel(
        **car.model_dump(),
        admin_id=current_user.id,
        image_url=image_url,
    )

    db.add(db_car)
    await db.commit()
    await db.refresh(db_car)
    return db_car


@router.put("/{car_id}", response_model=CarSchema)
async def update_car(
        car_id: int,
        car: CarCreate = Depends(CarCreate.as_form),
        image: UploadFile | None = File(None),
        db: AsyncSession = Depends(get_async_db),
        current_user: UserModel = Depends(get_current_admin)
):
    """
    Обновляет авто, если он принадлежит текущему салону (только для 'admin').
    """
    result = await db.scalars(select(CarModel).where(CarModel.id == car_id))
    db_car = result.first()
    if not db_car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found")
    if db_car.admin_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You can only update your own cars")
    brand_result = await db.scalars(
        select(BrandModel).where(BrandModel.id == car.brand_id,
                                    BrandModel.is_active == True)
    )
    if not brand_result.first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Brand not found or inactive")

    await db.execute(
        update(CarModel).where(CarModel.id == car_id).values(**car.model_dump())
    )

    if image:
        remove_car_image(db_car.image_url)
        db_car.image_url = await save_car_image(image)

    await db.commit()
    await db.refresh(db_car)
    return db_car


@router.delete("/{car_id}", response_model=CarSchema)
async def delete_car(
    car_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_admin)
):
    """
    Выполняет мягкое удаление авто, если он принадлежит текущему салону (только для 'admin').
    """
    result = await db.scalars(
        select(CarModel).where(CarModel.id == car_id, CarModel.is_active == True)
    )
    car = result.first()
    if not car:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Car not found or inactive")
    if car.admin_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own cars")
    await db.execute(
        update(CarModel).where(CarModel.id == car_id).values(is_active=False)
    )
    remove_car_image(car.image_url)

    await db.commit()
    await db.refresh(car)
    return car