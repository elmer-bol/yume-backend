# Archivo: app/services/categoria_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.db import models
from app.schemas import categoria_schema as schemas

class CategoriaService:
    def __init__(self, db: Session):
        self.db = db

    def get_categoria_by_id(self, categoria_id: int) -> Optional[models.Categoria]:
        return self.db.query(models.Categoria).filter(models.Categoria.id_catalogo == categoria_id).first()

    def get_all_categorias(self, filters: schemas.CategoriaFilter, skip: int = 0, limit: int = 100) -> List[models.Categoria]:
        query = self.db.query(models.Categoria)
        
        if filters.nombre_cuenta:
            query = query.filter(models.Categoria.nombre_cuenta.ilike(f"%{filters.nombre_cuenta}%"))
        if filters.tipo:
            query = query.filter(models.Categoria.tipo == filters.tipo)
        if filters.activo is not None:
            query = query.filter(models.Categoria.activo == filters.activo)
            
        return query.offset(skip).limit(limit).all()

    def create_categoria(self, categoria_in: schemas.CategoriaCreate) -> models.Categoria:
        # Validar duplicados
        existe = self.db.query(models.Categoria).filter(models.Categoria.nombre_cuenta == categoria_in.nombre_cuenta).first()
        if existe:
            raise ValueError(f"La cuenta '{categoria_in.nombre_cuenta}' ya existe.")

        db_categoria = models.Categoria(
            nombre_cuenta=categoria_in.nombre_cuenta,
            tipo=categoria_in.tipo,
            activo=categoria_in.activo
        )
        self.db.add(db_categoria)
        self.db.commit()
        self.db.refresh(db_categoria)
        return db_categoria

    def update_categoria(self, db_categoria: models.Categoria, categoria_in: schemas.CategoriaUpdate) -> models.Categoria:
        if categoria_in.nombre_cuenta and categoria_in.nombre_cuenta != db_categoria.nombre_cuenta:
             existe = self.db.query(models.Categoria).filter(models.Categoria.nombre_cuenta == categoria_in.nombre_cuenta).first()
             if existe:
                 raise ValueError(f"El nombre '{categoria_in.nombre_cuenta}' ya está en uso.")

        update_data = categoria_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_categoria, key, value)
            
        self.db.commit()
        self.db.refresh(db_categoria)
        return db_categoria

    def deactivate_categoria(self, db_categoria: models.Categoria) -> models.Categoria:
        db_categoria.activo = False
        self.db.commit()
        self.db.refresh(db_categoria)
        return db_categoria