from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# ----------------------------------------------------
# Base Schema
# ----------------------------------------------------
class MedioIngresoBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    tipo: str = Field(...)
    requiere_referencia: bool = Field(False)
    activo: bool = Field(True)
    
    # --- CORRECCIÓN AQUÍ ---
    # Quita el Optional. Quita el = None. Debe ser int obligatorio.
    id_catalogo: int = Field(..., description="ID de la Cuenta Contable")
# ----------------------------------------------------
# Create Schema
# ----------------------------------------------------
class MedioIngresoCreate(MedioIngresoBase):
    pass

# ----------------------------------------------------
# Update Schema
# ----------------------------------------------------
class MedioIngresoUpdate(MedioIngresoBase):
    # Todos opcionales para PATCH
    nombre: Optional[str] = Field(None, max_length=50)
    tipo: Optional[str] = None 
    requiere_referencia: Optional[bool] = None
    activo: Optional[bool] = None
    id_catalogo: Optional[int] = None # Permitimos cambiar la cuenta asociada

# ----------------------------------------------------
# Main Schema (Response)
# ----------------------------------------------------
class MedioIngreso(MedioIngresoBase):
    id_medio_ingreso: int

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# Simple Schema (Lookup)
# ----------------------------------------------------
class MedioIngresoSimple(BaseModel):
    id_medio_ingreso: int
    nombre: str

    model_config = ConfigDict(from_attributes=True)