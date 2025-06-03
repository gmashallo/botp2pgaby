from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class AdType(str, Enum):
    """Enum for ad types"""
    BUY = "BUY"
    SELL = "SELL"

class AdInfo(BaseModel):
    """Model for individual ad information"""
    price: float = Field(..., description="Price of the ad")
    nickname: str = Field(..., description="Nickname of the trader")

class TopPriceResponse(BaseModel):
    """Response model for top price endpoint"""
    buy: Optional[AdInfo] = Field(None, description="Top BUY ad information")
    sell: Optional[AdInfo] = Field(None, description="Top SELL ad information")
