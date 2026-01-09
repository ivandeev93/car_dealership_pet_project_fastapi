from pydantic import BaseModel, Field, ConfigDict, EmailStr
from decimal import Decimal
from datetime import datetime
from typing import Optional, Annotated

from fastapi import Form



class BrandCreate(BaseModel):
    """
    Модель для создания и обновления брендов.
    Используется в POST и PUT запросах.
    """
    name: str = Field(min_length=3, max_length=50,
                      description="Название бренда (3-50 символов)")


class Brand(BaseModel):
    """
    Модель для ответа с данными бренда.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор бренда")
    name: str = Field(description="Название бренда")
    is_active: bool = Field(description="Активность бренда")

    model_config = ConfigDict(from_attributes=True)


class CarCreate(BaseModel):
    """
    Модель для создания и обновления автомобиля.
    Используется в POST и PUT запросах.
    """
    name: str = Field(min_length=3, max_length=100,
                      description="Название автомобиля (3-100 символов)")
    description: str | None = Field(None, max_length=500,
                                       description="Описание автомобиля (до 500 символов)")
    price: Decimal = Field(gt=0, description="Цена автомобиля (больше 0)", decimal_places=2)
    stock: int = Field(ge=0, description="Количество автомобилей в наличии (0 или больше)")
    brand_id: int = Field(description="ID бренда, к которому относится автомобиль")

    @classmethod
    def as_form(
            cls,
            name: Annotated[str, Form(...)],
            price: Annotated[Decimal, Form(...)],
            stock: Annotated[int, Form(...)],
            brand_id: Annotated[int, Form(...)],
            description: Annotated[Optional[str], Form()] = None,
    ) -> "CarCreate":
        return cls(
            name=name,
            description=description,
            price=price,
            stock=stock,
            brand_id=brand_id,
        )


class Car(BaseModel):
    """
    Модель для ответа с данными автомобиля.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор автомобиля")
    name: str = Field(description="Название автомобиля")
    description: str | None = Field(None, description="Описание автомобиля")
    price: Decimal = Field(description="Цена автомобиля в рублях", gt=0, decimal_places=2)
    image_url: str | None = Field(None, description="URL изображения автомобиля")
    stock: int = Field(description="Количество автомобилей в наличии")
    brand_id: int = Field(description="ID бренда")
    is_active: bool = Field(description="Активность автомобиля")

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """
    Модель для создания и обновления пользователя.
    Используется в POST и PUT запросах.
    """
    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символов)")
    role: str = Field(default="buyer", pattern="^(buyer|admin)$", description="Роль: 'buyer' или 'admin'")


class User(BaseModel):
    """
    Модель для ответа с данными пользователя.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор пользователя")
    email: EmailStr = Field(description="Email пользователя")
    is_active: bool = Field(description="Активность пользователя")
    role: str = Field(description="Роль пользователя")

    model_config = ConfigDict(from_attributes=True)


class CarList(BaseModel):
    """
    Список пагинации для автомобилей.
    """
    items: list[Car] = Field(description="Автомобили для текущей страницы")
    total: int = Field(ge=0, description="Общее количество автомобилей")
    page: int = Field(ge=1, description="Номер текущей страницы")
    page_size: int = Field(ge=1, description="Количество элементов на странице")

    model_config = ConfigDict(from_attributes=True)

