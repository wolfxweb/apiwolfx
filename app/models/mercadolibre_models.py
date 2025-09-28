from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class MLToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: str
    user_id: int
    refresh_token: Optional[str] = None


class MLUser(BaseModel):
    id: int
    nickname: str
    email: str
    first_name: str
    last_name: str
    country_id: str
    site_id: str
    permalink: str


class MLItem(BaseModel):
    id: str
    title: str
    category_id: str
    price: float
    currency_id: str
    seller_id: int
    condition: str
    permalink: str
    thumbnail: str
    pictures: Optional[List[Dict[str, Any]]] = None
    attributes: Optional[List[Dict[str, Any]]] = None


class MLSearchResponse(BaseModel):
    site_id: str
    country_default_time_zone: str
    query: str
    paging: Dict[str, Any]
    results: List[MLItem]


class MLCategory(BaseModel):
    id: str
    name: str
    picture: Optional[str] = None
    permalink: Optional[str] = None
    total_items_in_this_category: int
    path_from_root: Optional[List[Dict[str, str]]] = None


class MLError(BaseModel):
    message: str
    error: str
    status: int


class AuthResponse(BaseModel):
    """Modelo para resposta de autenticação"""
    success: bool
    message: str
    token: Optional[MLToken] = None
    user: Optional[MLUser] = None
