from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.db import models
from app.schemas import tipo_egreso_schema as schemas

class TipoEgresoService:
    def __init__(self, db: Session):
        self.db = db

    def _get_by_id_or_error(self, id: int) -> models.TipoEgreso:
        item = self.db.query(models.TipoEgreso).filter(models.TipoEgreso.id_tipo_egreso == id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Tipo de Egreso no encontrado")
        return item

    # ### NUEVO: Helper para validar el Rubro ###
    def _validar_rubro(self, id_catalogo: Optional[int]):
        if id_catalogo:
            rubro = self.db.query(models.Categoria).filter(models.Categoria.id_catalogo == id_catalogo).first()
            if not rubro:
                raise HTTPException(status_code=404, detail="El Rubro Contable especificado no existe.")
            if not rubro.es_rubro:
                raise HTTPException(status_code=400, detail="El vínculo debe ser a un RUBRO (Carpeta), no a una cuenta imputable.")

    # --- LECTURA ---
    def get_by_id(self, id: int) -> models.TipoEgreso:
        return self._get_by_id_or_error(id)

    def get_all(self, skip: int = 0, limit: int = 100, include_inactive: bool = False) -> List[models.TipoEgreso]:
        query = self.db.query(models.TipoEgreso)
        if not include_inactive:
            query = query.filter(models.TipoEgreso.activo == True)
        return query.order_by(models.TipoEgreso.nombre).offset(skip).limit(limit).all()

    # --- CREACIÓN ---
    def create(self, tipo_in: schemas.TipoEgresoCreate) -> models.TipoEgreso:
        # 1. Validar duplicados de nombre
        existe = self.db.query(models.TipoEgreso).filter(models.TipoEgreso.nombre == tipo_in.nombre).first()
        if existe:
            raise HTTPException(status_code=409, detail=f"El grupo '{tipo_in.nombre}' ya existe.")

        # 2. ### NUEVO: Validar Rubro Contable ###
        self._validar_rubro(tipo_in.id_catalogo)

        # 3. Crear
        nuevo = models.TipoEgreso(
            nombre=tipo_in.nombre,
            requiere_num_doc=tipo_in.requiere_num_doc,
            id_catalogo=tipo_in.id_catalogo, # <--- Guardamos el ID
            activo=True
        )
        self.db.add(nuevo)
        self.db.commit()
        self.db.refresh(nuevo)
        return nuevo

    # --- ACTUALIZACIÓN ---
    def update(self, id: int, tipo_in: schemas.TipoEgresoUpdate) -> models.TipoEgreso:
        db_obj = self._get_by_id_or_error(id)

        # Validar nombre duplicado
        if tipo_in.nombre and tipo_in.nombre != db_obj.nombre:
            existe = self.db.query(models.TipoEgreso).filter(models.TipoEgreso.nombre == tipo_in.nombre).first()
            if existe:
                raise HTTPException(status_code=409, detail=f"El nombre '{tipo_in.nombre}' ya está en uso.")

        # ### NUEVO: Validar si cambia el rubro ###
        if tipo_in.id_catalogo is not None:
             self._validar_rubro(tipo_in.id_catalogo)

        update_data = tipo_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    # --- SOFT DELETE (Corregido nombre para el endpoint) ---
    def soft_delete(self, id: int) -> models.TipoEgreso:
        db_obj = self._get_by_id_or_error(id)
        if not db_obj.activo:
             raise HTTPException(status_code=400, detail="El grupo ya se encuentra inactivo.")
        
        db_obj.activo = False
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj

    # --- REACTIVAR ---
    def activate(self, id: int) -> models.TipoEgreso:
        db_obj = self._get_by_id_or_error(id)
        if db_obj.activo:
             raise HTTPException(status_code=400, detail="El grupo ya se encuentra activo.")
        
        db_obj.activo = True
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj