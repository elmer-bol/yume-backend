# Archivo: app/services/categoria_service.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status
from typing import List, Optional

from app.db import models
from app.schemas import categoria_schema as schemas

class CategoriaService:
    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. LECTURA CON FILTROS AVANZADOS
    # -------------------------------------------------------------------------
    def get_all_categorias(self, 
                           nombre: Optional[str] = None, 
                           tipo: Optional[str] = None, 
                           activo: Optional[bool] = None,
                           es_rubro: Optional[bool] = None,
                           skip: int = 0, 
                           limit: int = 100):
        """
        Recupera cuentas aplicando filtros opcionales.
        """
        query = self.db.query(models.Categoria)

        if nombre:
            # Búsqueda insensible a mayúsculas (ILIKE en Postgres, pero usamos pythonic filter para compatibilidad)
            query = query.filter(models.Categoria.nombre_cuenta.ilike(f"%{nombre}%"))
        
        if tipo:
            query = query.filter(models.Categoria.tipo == tipo)
        
        if activo is not None:
            query = query.filter(models.Categoria.activo == activo)
        
        if es_rubro is not None:
            query = query.filter(models.Categoria.es_rubro == es_rubro)

        # Ordenar por CÓDIGO es vital en contabilidad (1.1, 1.2, 1.2.1...)
        return query.order_by(models.Categoria.codigo).offset(skip).limit(limit).all()

    def get_categoria_by_id(self, id_catalogo: int):
        return self.db.query(models.Categoria).filter(models.Categoria.id_catalogo == id_catalogo).first()

    # -------------------------------------------------------------------------
    # 2. CREACIÓN CON VALIDACIÓN JERÁRQUICA
    # -------------------------------------------------------------------------
    def crear_categoria(self, categoria_in: schemas.CategoriaCreate):
        # A. Validar Duplicados
        if self.db.query(models.Categoria).filter(models.Categoria.codigo == categoria_in.codigo).first():
            raise HTTPException(status_code=400, detail=f"El código contable '{categoria_in.codigo}' ya existe.")
        
        if self.db.query(models.Categoria).filter(models.Categoria.nombre_cuenta == categoria_in.nombre_cuenta).first():
            raise HTTPException(status_code=400, detail=f"La cuenta '{categoria_in.nombre_cuenta}' ya existe.")

        # B. Validar Padre (Lógica de Negocio)
        # Si creo "1.1.05", debe existir "1.1" o "1.1.0" dependiendo de tu nomenclatura.
        # Asumiremos separación por puntos.
        partes = categoria_in.codigo.split('.')
        if len(partes) > 1:
            # Reconstruir el padre (ej: de 1.1.01 -> padre es 1.1)
            codigo_padre = ".".join(partes[:-1]) 
            padre = self.db.query(models.Categoria).filter(models.Categoria.codigo == codigo_padre).first()
            
            # Opcional: Descomenta esto si quieres ser estricto
            # if not padre:
            #     raise HTTPException(status_code=400, detail=f"No se puede crear '{categoria_in.codigo}' porque el nivel superior '{codigo_padre}' no existe.")

        # C. Crear Registro
        nueva_cat = models.Categoria(
            codigo=categoria_in.codigo,
            nombre_cuenta=categoria_in.nombre_cuenta,
            tipo=categoria_in.tipo,
            es_rubro=categoria_in.es_rubro,
            activo=categoria_in.activo
        )
        self.db.add(nueva_cat)
        self.db.commit()
        self.db.refresh(nueva_cat)
        return nueva_cat

    # -------------------------------------------------------------------------
    # 3. ACTUALIZACIÓN SEGURA
    # -------------------------------------------------------------------------
    def actualizar_categoria(self, id_catalogo: int, data_in: schemas.CategoriaUpdate):
        cat_db = self.get_categoria_by_id(id_catalogo)
        if not cat_db:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")

        # Validar cambio de código duplicado
        if data_in.codigo and data_in.codigo != cat_db.codigo:
             if self.db.query(models.Categoria).filter(models.Categoria.codigo == data_in.codigo).first():
                raise HTTPException(status_code=400, detail="El nuevo código ya está en uso.")

        # Actualizar campos
        update_data = data_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(cat_db, field, value)

        self.db.commit()
        self.db.refresh(cat_db)
        return cat_db

    # -------------------------------------------------------------------------
    # 4. ELIMINACIÓN INTELIGENTE (Hard Delete con protección)
    # -------------------------------------------------------------------------
    def eliminar_categoria(self, id_catalogo: int):
        cat_db = self.get_categoria_by_id(id_catalogo)
        if not cat_db:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        
        # A. Protección de Hijos (No borrar padre si tiene hijos)
        # Buscamos si existe alguna cuenta que empiece con este código + punto
        # Ej: Si borro "1.1", busco cualquiera que empiece con "1.1."
        hijos = self.db.query(models.Categoria).filter(
            models.Categoria.codigo.like(f"{cat_db.codigo}.%")
        ).first()

        if hijos:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede eliminar la cuenta '{cat_db.codigo}' porque tiene sub-cuentas dependientes. Elimine las hijas primero."
            )

        # B. Protección de Integridad (Foreign Keys)
        # Intentamos borrar. Si la BD grita porque hay Egresos/Ingresos asociados, capturamos el error.
        try:
            self.db.delete(cat_db)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # Analizar si es error de integridad (psycopg2)
            raise HTTPException(
                status_code=400, 
                detail="No se puede eliminar: Esta cuenta ya tiene movimientos contables (Ingresos/Egresos/Medios) asociados. Intente desactivarla en su lugar."
            )
        
        return {"message": "Cuenta eliminada correctamente"}
    
    # -------------------------------------------------------------------------
    # 5. DESACTIVAR (Soft Delete)
    # -------------------------------------------------------------------------
    def deactivate_categoria(self, id_catalogo: int):
        """Alternativa segura: Marcar como inactiva en lugar de borrar."""
        cat_db = self.get_categoria_by_id(id_catalogo)
        if not cat_db:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")
        
        cat_db.activo = False
        self.db.commit()
        self.db.refresh(cat_db)
        return cat_db