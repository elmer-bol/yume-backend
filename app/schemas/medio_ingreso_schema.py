from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

# ----------------------------------------------------
# Base Schema (Campos Comunes)
# ----------------------------------------------------
class MedioIngresoBase(BaseModel):
    nombre: str = Field(..., max_length=50)
    tipo: str = Field(..., description="Ej: Efectivo, Banco, Digital")
    requiere_referencia: bool = Field(False)
    activo: bool = Field(True)
    
    # --- NUEVO: Regla de Negocio (Límite 1000 Bs) ---
    limite_maximo: float = Field(0.0, description="Monto máximo permitido por movimiento (0 = Sin límite)")

# ----------------------------------------------------
# Create Schema (Input)
# ----------------------------------------------------
class MedioIngresoCreate(MedioIngresoBase):
    # El enlace contable es OBLIGATORIO al crear
    id_catalogo: int = Field(..., description="ID de la Cuenta Contable de ACTIVO (Ej: 1.1.01)")

# ----------------------------------------------------
# Update Schema (Input - Patch)
# ----------------------------------------------------
class MedioIngresoUpdate(BaseModel):
    # Todos opcionales para PATCH
    nombre: Optional[str] = Field(None, max_length=50)
    tipo: Optional[str] = None 
    requiere_referencia: Optional[bool] = None
    activo: Optional[bool] = None
    
    id_catalogo: Optional[int] = None     # Permitimos cambiar la cuenta asociada
    limite_maximo: Optional[float] = None # Permitimos cambiar el límite

# ----------------------------------------------------
# Main Schema (Response - Output)
# ----------------------------------------------------
# CAMBIO: Renombrado a 'MedioIngresoResponse' para consistencia
class MedioIngresoResponse(MedioIngresoBase):
    id_medio_ingreso: int
    
    # Incluimos el ID de catálogo que viene de la BD
    id_catalogo: int 
    
    # --- NUEVO: Datos visuales para el Frontend ---
    # Esto permite mostrar "Caja Chica - 1.1.01" en la tabla
    nombre_cuenta: Optional[str] = "Sin Asignar"
    codigo_cuenta: Optional[str] = ""

    model_config = ConfigDict(from_attributes=True)

# ----------------------------------------------------
# Simple Schema (Lookup / Dropdowns)
# ----------------------------------------------------
class MedioIngresoSimple(BaseModel):
    id_medio_ingreso: int
    nombre: str
    limite_maximo: float = 0.0 # Útil para validaciones rápidas en el front

    model_config = ConfigDict(from_attributes=True)