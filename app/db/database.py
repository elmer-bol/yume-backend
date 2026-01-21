from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
# IMPORTANTE: Aquí importamos la configuración que acabamos de crear
from app.core.config import settings

# 1. Crear el motor (Engine)
# En lugar de escribir la URL aquí, la traemos de settings.DATABASE_URL
engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping=True es muy útil: verifica que la conexión siga viva
    # antes de intentar usarla (evita errores si la BD se reinicia).
    pool_pre_ping=True
)

# 2. Configurar la Sesión (Igual que antes)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Base Declarativa (Igual que antes)
Base = declarative_base()

# 4. Dependencia para obtener la DB (Igual que antes)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()