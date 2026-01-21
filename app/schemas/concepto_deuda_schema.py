# Archivo: app/schemas/concepto_deuda_schema.py
from pydantic import BaseModel
from typing import Optional

class ConceptoDeudaBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
   
    activo: bool = True

class ConceptoDeudaCreate(ConceptoDeudaBase):
    pass

# --- AGREGA ESTO SI NO LO TIENES ---
class ConceptoDeudaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

    activo: Optional[bool] = None
# -----------------------------------

class ConceptoDeuda(ConceptoDeudaBase):
    id_concepto: int

    class Config:
        from_attributes = True