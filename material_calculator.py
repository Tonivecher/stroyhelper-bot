
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class MaterialUnit(Enum):
    SQUARE_METER = "м²"
    LINEAR_METER = "м"
    PIECE = "шт"
    ROLL = "рулон"

@dataclass
class MaterialCalculation:
    area: float
    price_per_unit: float
    unit: MaterialUnit
    waste_percent: float = 5
    discount_percent: float = 0

    def calculate(self) -> Dict[str, float]:
        base_amount = self.area
        if self.unit == MaterialUnit.SQUARE_METER:
            # Добавляем процент на подрезку
            base_amount *= (1 + self.waste_percent / 100)
        
        base_cost = base_amount * self.price_per_unit
        discount = base_cost * (self.discount_percent / 100)
        total_cost = base_cost - discount

        return {
            "amount": round(base_amount, 2),
            "base_cost": round(base_cost, 2),
            "discount": round(discount, 2),
            "total_cost": round(total_cost, 2)
        }
