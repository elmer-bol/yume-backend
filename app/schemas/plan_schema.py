# Archivo: app/schemas/plan_schema.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

# --- INPUT: Lo que recibimos del Frontend ---
class PlanPagoCreate(BaseModel):
    id_persona: int
    items_ids: List[int]  # Los IDs de las deudas viejas que vamos a "Congelar"
    
    # Datos del acuerdo
    numero_cuotas: int
    monto_cuota_mensual: Decimal
    fecha_inicio_pago: date  # Cuándo vence la primera cuota nueva
    observaciones: Optional[str] = None

# --- OUTPUT: Lo que respondemos ---
class PlanPagoResponse(BaseModel):
    id_plan: int
    monto_total_deuda: Decimal
    estado: str
    numero_cuotas: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True