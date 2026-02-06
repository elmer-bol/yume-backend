from sqlalchemy.orm import Session
from sqlalchemy import asc
from datetime import date
from dateutil.relativedelta import relativedelta # Necesitarás: pip install python-dateutil
from fastapi import HTTPException
from decimal import Decimal

from app.db.models import PlanPago, ItemFacturable, ConceptoDeuda
from app.schemas.plan_schema import PlanPagoCreate

def crear_plan_de_pagos(db: Session, datos: PlanPagoCreate, user_id_creador: int):
    # 1. Validaciones previas
    # Buscamos las deudas que quiere refinanciar
    items_a_congelar = db.query(ItemFacturable).filter(
        ItemFacturable.id_item.in_(datos.items_ids),
        ItemFacturable.id_persona == datos.id_persona,
        ItemFacturable.estado == 'pendiente'
    ).all()

    if len(items_a_congelar) != len(datos.items_ids):
        raise HTTPException(status_code=400, detail="Algunos items no existen, no son de la persona o ya no están pendientes.")

    # Calculamos el monto total real
    total_deuda = sum(item.saldo_pendiente for item in items_a_congelar)

    # 2. Crear la Cabecera del Plan
    nuevo_plan = PlanPago(
        id_persona=datos.id_persona,
        monto_total_deuda=total_deuda,
        numero_cuotas=datos.numero_cuotas,
        monto_cuota_mensual=datos.monto_cuota_mensual,
        fecha_inicio=datos.fecha_inicio_pago,
        observaciones=datos.observaciones,
        estado='activo'
    )
    db.add(nuevo_plan)
    db.flush() # Para obtener el ID del plan antes del commit final

    # 3. FASE A: Congelar las deudas viejas
    for item in items_a_congelar:
        item.estado = 'congelado'
        item.id_plan = nuevo_plan.id_plan
        item.monto_abonado = 0  # Inicializamos en 0
        # Opcional: item.bloqueo_pago_automatico = True
    
    # 4. FASE B: Generar las nuevas Cuotas (Futuro)
    # Buscamos el concepto "Cuota Plan de Pagos" (Asegúrate que exista en BD)
    concepto_plan = db.query(ConceptoDeuda).filter(ConceptoDeuda.nombre == "Cuota Plan de Pagos").first()
    if not concepto_plan:
        raise HTTPException(status_code=500, detail="El concepto 'Cuota Plan de Pagos' no existe en el sistema.")

    fecha_iteracion = datos.fecha_inicio_pago
    
    # Tomamos la Unidad del primer item viejo (asumiendo que refinancia cosas de su misma unidad)
    unidad_ref = items_a_congelar[0].id_unidad

    for i in range(1, datos.numero_cuotas + 1):
        nueva_cuota = ItemFacturable(
            id_unidad=unidad_ref,
            id_concepto=concepto_plan.id_concepto,
            id_persona=datos.id_persona,
            id_plan=nuevo_plan.id_plan, # Vinculamos al mismo plan
            
            monto_base=datos.monto_cuota_mensual,
            saldo_pendiente=datos.monto_cuota_mensual,
            monto_abonado=0,
            
            periodo=f"Cuota {i}/{datos.numero_cuotas}",
            fecha_vencimiento=fecha_iteracion,
            estado='pendiente',
            
            mes=fecha_iteracion.month,
            año=fecha_iteracion.year,
            
            id_usuario_creador=user_id_creador
        )
        db.add(nueva_cuota)
        
        # Sumamos 1 mes para la siguiente cuota
        fecha_iteracion = fecha_iteracion + relativedelta(months=1)

    # 5. Guardar todo
    db.commit()
    db.refresh(nuevo_plan)
    return nuevo_plan

def procesar_abono_a_plan(db: Session, item_cuota_pagada: ItemFacturable, monto_pagado: Decimal):
    """
    LOGICA DE CASCADA (GOTEO):
    Cuando se paga una 'Cuota de Plan', este dinero debe distribuirse 
    entre las deudas viejas 'CONGELADAS' de ese mismo plan.
    """
    if not item_cuota_pagada.id_plan:
        return  # No es parte de un plan, no hacemos nada extra.

    # 1. Obtenemos el plan
    plan = db.query(PlanPago).get(item_cuota_pagada.id_plan)
    if not plan:
        return

    # 2. Buscamos las deudas congeladas (ordenadas por antigüedad)
    # Solo nos interesan las que NO se han terminado de pagar (monto_abonado < monto_base)
    items_congelados = db.query(ItemFacturable).filter(
        ItemFacturable.id_plan == plan.id_plan,
        ItemFacturable.estado == 'congelado',
        ItemFacturable.monto_abonado < ItemFacturable.monto_base  # Filtro clave
    ).order_by(asc(ItemFacturable.fecha_vencimiento)).all()

    remanente = monto_pagado

    # 3. El Bucle de Llenado (Waterfall)
    for item_viejo in items_congelados:
        if remanente <= 0:
            break

        # ¿Cuánto le falta a este item viejo para llenarse?
        # saldo_real = Lo que valía - Lo que ya le hemos metido antes
        saldo_real_por_cubrir = item_viejo.monto_base - item_viejo.monto_abonado

        if remanente >= saldo_real_por_cubrir:
            # A) ALCANZA PARA CUBRIR TODO EL ITEM
            item_viejo.monto_abonado += saldo_real_por_cubrir # Llenamos el vaso
            item_viejo.estado = 'pagado' # ¡Deuda vieja saldada!
            remanente -= saldo_real_por_cubrir
        else:
            # B) SOLO ALCANZA PARA UNA PARTE (Abono Parcial)
            item_viejo.monto_abonado += remanente
            # El estado sigue siendo 'congelado' pero con más dinero adentro
            remanente = 0
    
    # 4. Verificar si el Plan se completó totalmente
    # (Opcional: Si ya no quedan items congelados pendientes, marcar el Plan como COMPLETADO)
    pendientes = db.query(ItemFacturable).filter(
        ItemFacturable.id_plan == plan.id_plan,
        ItemFacturable.estado == 'congelado',
        ItemFacturable.monto_abonado < ItemFacturable.monto_base
    ).count()
    
    if pendientes == 0:
        plan.estado = 'completado'

    db.add(plan)
    # Nota: No hacemos db.commit() aquí, porque esta función se llama dentro
    # de la transacción grande del cobro.