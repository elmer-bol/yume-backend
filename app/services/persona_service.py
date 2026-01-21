# Archivo: app/services/persona_service.py
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import models
from app.schemas import persona_schema as schemas

# Excepción personalizada que tu endpoint espera importar
class PersonaNotFoundError(Exception):
    pass

class PersonaService:
    def __init__(self, db: Session):
        self.db = db

    def get_persona_by_id(self, persona_id: int) -> Optional[models.Persona]:
        return self.db.query(models.Persona).filter(models.Persona.id_persona == persona_id).first()

    def get_all_personas(self, skip: int = 0, limit: int = 100) -> List[models.Persona]:
        return self.db.query(models.Persona).offset(skip).limit(limit).all()

    def get_filtered_personas(self, filters: schemas.PersonaFilter) -> List[models.Persona]:
        query = self.db.query(models.Persona)
        
        if filters.nombres:
            query = query.filter(models.Persona.nombres.ilike(f"%{filters.nombres}%"))
        if filters.apellidos:
            query = query.filter(models.Persona.apellidos.ilike(f"%{filters.apellidos}%"))
        if filters.telefono:
            query = query.filter(models.Persona.telefono.like(f"%{filters.telefono}%"))
        if filters.activo is not None:
            query = query.filter(models.Persona.activo == filters.activo)
            
        return query.all()

    def create_persona(self, persona_in: schemas.PersonaCreate) -> models.Persona:
        # Aquí podrías validar CI duplicado si quisieras
        db_persona = models.Persona(
            nombres=persona_in.nombres,
            apellidos=persona_in.apellidos,
            telefono=persona_in.telefono,
            celular=persona_in.celular,
            email=persona_in.email,
            activo=True
        )
        self.db.add(db_persona)
        self.db.commit()
        self.db.refresh(db_persona)
        return db_persona

    def update_persona(self, persona_id: int, persona_in: schemas.PersonaUpdate) -> models.Persona:
        db_persona = self.get_persona_by_id(persona_id)
        if not db_persona:
            raise PersonaNotFoundError(f"La persona con id {persona_id} no existe.")

        update_data = persona_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_persona, field, value)

        self.db.commit()
        self.db.refresh(db_persona)
        return db_persona

    def soft_delete_persona(self, persona_id: int) -> models.Persona:
        db_persona = self.get_persona_by_id(persona_id)
        if not db_persona:
            raise PersonaNotFoundError(f"La persona con id {persona_id} no existe.")
        
        db_persona.activo = False
        self.db.commit()
        self.db.refresh(db_persona)
        return db_persona