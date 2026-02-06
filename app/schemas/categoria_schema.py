# Archivo: app/schemas/categoria_schema.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# -----------------------------------------------------------------------------
# CONSTANTES / ENUMS
# -----------------------------------------------------------------------------
class TipoCategoriaEnum:
    """
    Define los valores permitidos para el tipo de cuenta.
    Esto evita errores de dedo (typos) en el frontend o backend.
    """
    ACTIVO = "ACTIVO"   # Caja, Bancos
    PASIVO = "PASIVO"   # Deudas (Futuro)
    INGRESO = "INGRESO" # Cobros
    EGRESO = "EGRESO"   # Gastos

# -----------------------------------------------------------------------------
# 1. ESQUEMA BASE (Reglas comunes)
# -----------------------------------------------------------------------------
class CategoriaBase(BaseModel):
    codigo: str = Field(
        ..., 
        min_length=1, 
        max_length=20, 
        description="Código jerárquico contable (Ej: '1.1.01'). Debe ser único.",
        examples=["1.1.01", "5.2.1"]
    )
    
    nombre_cuenta: str = Field(
        ..., 
        min_length=3, 
        max_length=100, 
        description="Nombre descriptivo de la cuenta.",
        examples=["Caja Chica", "Servicios Básicos"]
    )
    
    tipo: str = Field(
        ..., 
        description=f"Categoría mayor: {TipoCategoriaEnum.ACTIVO}, {TipoCategoriaEnum.INGRESO}, {TipoCategoriaEnum.EGRESO}"
    )
    
    es_rubro: bool = Field(
        False, 
        description="True = Título agrupador (No recibe dinero). False = Cuenta imputable."
    )
    
    activo: bool = Field(
        True, 
        description="Indica si la cuenta está disponible para operaciones."
    )

# -----------------------------------------------------------------------------
# 2. ESQUEMA DE CREACIÓN (POST)
# -----------------------------------------------------------------------------
class CategoriaCreate(CategoriaBase):
    """
    Validaciones extra al crear. Por ahora hereda todo de Base.
    """
    pass

# -----------------------------------------------------------------------------
# 3. ESQUEMA DE ACTUALIZACIÓN (PATCH/PUT)
# -----------------------------------------------------------------------------
class CategoriaUpdate(BaseModel):
    """
    Todos los campos son opcionales porque en un PATCH puedes querer
    cambiar solo el nombre y dejar el código igual.
    """
    codigo: Optional[str] = Field(None, max_length=20)
    nombre_cuenta: Optional[str] = Field(None, max_length=100)
    tipo: Optional[str] = None
    es_rubro: Optional[bool] = None
    activo: Optional[bool] = None

# -----------------------------------------------------------------------------
# 4. ESQUEMA DE FILTRADO (Query Params)
# -----------------------------------------------------------------------------
class CategoriaFilter(BaseModel):
    """
    Estructura para recibir parámetros de búsqueda en el GET.
    """
    nombre_cuenta: Optional[str] = Field(None, description="Búsqueda parcial por nombre")
    tipo: Optional[str] = Field(None, description="Filtrar por ACTIVO/INGRESO/EGRESO")
    activo: Optional[bool] = None

# -----------------------------------------------------------------------------
# 5. ESQUEMA DE RESPUESTA (Output)
# -----------------------------------------------------------------------------
class CategoriaResponse(CategoriaBase):
    """
    Lo que devuelve la API al Frontend. Incluye el ID interno de la BD.
    """
    id_catalogo: int = Field(..., description="ID autogenerado por la base de datos")

    class Config:
        # Esto es vital para que Pydantic lea los objetos de SQLAlchemy
        from_attributes = True