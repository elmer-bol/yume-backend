from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

# --- Clase auxiliar ---
class ConceptoDeudaSimple(BaseModel):
    nombre: str
    class Config:
        from_attributes = True

# --- 1. Esquema Base ---
class ItemFacturableBase(BaseModel):
    id_unidad: int = Field(..., description="ID de la Unidad de Servicio.")
    id_persona: int = Field(..., description="ID del Cliente.")
    id_concepto: int = Field(..., description="ID del Concepto.")
    monto_base: Optional[float] = Field(None, gt=0, description="Monto.")
    periodo: str = Field(..., max_length=10, description="Format YYYY-MM")
    fecha_vencimiento: date = Field(..., description="Fecha límite.")
    concepto: Optional[ConceptoDeudaSimple] = None

# --- 2. Esquema Creación (Input) ---
class ItemFacturableCreate(ItemFacturableBase):
    pass 
    # NO PEDIMOS id_usuario AQUÍ. El backend lo inyecta.

# --- 3. Esquema Actualización ---
class ItemFacturableUpdate(BaseModel):
    id_unidad: Optional[int] = Field(None)
    id_persona: Optional[int] = Field(None)
    id_concepto: Optional[int] = Field(None)
    monto_base: Optional[float] = Field(None, gt=0)
    periodo: Optional[str] = Field(None, max_length=10)
    fecha_vencimiento: Optional[date] = Field(None)
    class Config:
        from_attributes = True

# --- 4. Esquema Lectura (Response) ---
class ItemFacturable(ItemFacturableBase):
    id_unidad: int
    id_item: int
    estado: str = Field(..., max_length=20)
    saldo_pendiente: float
    año: Optional[int] = Field(None)
    mes: Optional[int] = Field(None)
    
    # AUDITORÍA EN RESPUESTA
    id_usuario_creador: Optional[int] = None
    id_usuario_modificacion: Optional[int] = None
    
    fecha_creacion: datetime
    fecha_modificacion: datetime
    
    class Config:
        from_attributes = True

# --- 5. Esquema Filtro ---
class ItemFacturableFilter(BaseModel):
    id_persona: Optional[int] = None
    id_unidad: Optional[int] = None
    id_concepto: Optional[int] = None
    estado: Optional[str] = None
    periodo: Optional[str] = None
    fecha_vencimiento_min: Optional[date] = None
    fecha_vencimiento_max: Optional[date] = None
    saldo_pendiente_min: Optional[float] = None
    saldo_pendiente_max: Optional[float] = None
    
    def is_empty(self):
        return not any([
            self.id_persona, self.id_unidad, self.id_concepto, self.estado, 
            self.periodo, self.fecha_vencimiento_min, self.fecha_vencimiento_max
        ])

# --- 6. GENERACIÓN INTELIGENTE ---
class GenerarCuotaRequest(BaseModel):
    id_unidad: int
    id_concepto: int
    periodo: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    fecha_vencimiento: date
    id_persona: Optional[int] = None
    monto_base: Optional[float] = None

class GenerarMasivoRequest(BaseModel):
    id_unidad: int
    id_concepto: int
    periodo_inicio: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    cantidad_meses: int = Field(..., gt=0, le=24)
    id_persona: Optional[int] = None
    monto_base: Optional[float] = None

class GenerarGlobalRequest(BaseModel):
    id_concepto: int = Field(..., description="Concepto a cobrar")
    periodo: str = Field(..., pattern=r"^\d{4}-\d{2}$")

# Agrega esta clase al final de tu archivo schema
class GenerarPorContratoRequest(BaseModel):
    id_unidad: int
    id_persona: int      # El inquilino del contrato
    id_concepto: int     # Ej: Expensas (ID 1)
    
    periodo_inicio: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM (Ej: 2025-01)")
    cantidad_meses: int = Field(..., gt=0, le=24, description="Cuántos meses generar desde esa fecha")
    
    # Opcional: Si quieres forzar un monto distinto al del contrato
    monto_override: Optional[float] = None