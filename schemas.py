from pydantic import BaseModel, Field, HttpUrl, constr, conlist
from typing import List

class Card(BaseModel):
    title: constr(strip_whitespace=True, min_length=2, max_length=120)
    summary: constr(strip_whitespace=True, min_length=5, max_length=400)
    blocks: conlist(constr(strip_whitespace=True, min_length=5), min_length=1, max_length=8)
    tips: List[constr(strip_whitespace=True, min_length=2)] = []
    sources: List[HttpUrl] = []

    class Config:
        extra = "ignore"  # игнорировать лишние поля
