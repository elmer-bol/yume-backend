# Archivo: app/schemas/persona_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# --- Esquemas Base ---

class PersonaBase(BaseModel):
    """Esquema base con campos comunes de Persona."""
    nombres: str = Field(..., max_length=50, description="Nombres de la persona.")
    apellidos: str = Field(..., max_length=50, description="Apellidos de la persona.")
    
    # CRÍTICO: Son NOT NULL en models.py, deben ser requeridos en Pydantic
    telefono: str = Field(..., max_length=15)
    celular: str = Field(..., max_length=15)
    
    email: Optional[str] = Field(None, max_length=100) # Opcional en models.py
    activo: bool = Field(True, description="Estado de actividad de la persona.") # Default en models.py
    

# --- Esquemas de Entrada (Input) ---

class PersonaCreate(PersonaBase):
    """Esquema usado para crear un nuevo registro de Persona."""
    pass

class PersonaUpdate(BaseModel):
    """
    4. Esquema de Actualización (PUT/PATCH): 
    Todos los campos son opcionales, permitiendo la actualización parcial.
    """
    nombres: Optional[str] = Field(None, max_length=50)
    apellidos: Optional[str] = Field(None, max_length=50)
    telefono: Optional[str] = Field(None, max_length=15)
    celular: Optional[str] = Field(None, max_length=15)
    email: Optional[str] = Field(None, max_length=100)
    # Se incluye 'activo' para permitir la baja/alta lógica (Soft Delete)
    activo: Optional[bool] = None 


# --- Esquema de Filtro para Búsqueda (Query) ---

class PersonaFilter(BaseModel):
    """
    5. Esquema de Filtro para Búsqueda: 
    Define los parámetros opcionales para filtrar la lista de personas.
    """
    nombres: Optional[str] = Field(None, description="Filtrar por nombres parciales.")
    apellidos: Optional[str] = Field(None, description="Filtrar por apellidos parciales.")
    telefono: Optional[str] = Field(None, description="Filtrar por número de teléfono exacto.")
    activo: Optional[bool] = Field(True, description="Filtrar por estado activo (por defecto, True).")
    

# --- Esquema de Salida (Response) ---

class Persona(PersonaBase):
    """
    3. Esquema de Lectura (Para retornar los datos, incluyendo campos de auditoría)
    """
    id_persona: int
    fecha_creacion: datetime # Añadir el campo de auditoría

    class Config:
        # Pydantic v2+ utiliza from_attributes
        from_attributes = True