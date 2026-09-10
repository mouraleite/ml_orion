import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.security import get_password_hash
from app.db.database import Base
from app.models.user import User
from app.models.viability import Viability
from app.models.phase import Phase
from app.models.snapshot import PhaseSnapshot
from app.models.curves import StandardCurve

def seed_users():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./viabilidades.db")
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    hashed_password = get_password_hash("senha123")
    
    with SessionLocal() as session:
        result = session.execute(text("SELECT id FROM users WHERE email = 'diretor@mouraleite.com.br'"))
        if not result.first():
            session.execute(text(f"""
                INSERT INTO users (email, full_name, hashed_password, role, is_active)
                VALUES ('diretor@mouraleite.com.br', 'Diretor Moura Leite', '{hashed_password}', 'DIRETOR', true)
            """))
            print("Diretor criado.")
            
        result = session.execute(text("SELECT id FROM users WHERE email = 'analista@mouraleite.com.br'"))
        if not result.first():
            session.execute(text(f"""
                INSERT INTO users (email, full_name, hashed_password, role, is_active)
                VALUES ('analista@mouraleite.com.br', 'Analista Moura Leite', '{hashed_password}', 'ANALISTA', true)
            """))
            print("Analista criado.")

        result = session.execute(text("SELECT id FROM users WHERE email = 'visitante@mouraleite.com.br'"))
        if not result.first():
            session.execute(text(f"""
                INSERT INTO users (email, full_name, hashed_password, role, is_active)
                VALUES ('visitante@mouraleite.com.br', 'Visitante', '{hashed_password}', 'VISITANTE', true)
            """))
            print("Visitante criado.")

        result = session.execute(text("SELECT id FROM users WHERE email = 'admin@mouraleite.com.br'"))
        if not result.first():
            hashed_admin_password = get_password_hash("admin")
            session.execute(text(f"""
                INSERT INTO users (email, full_name, hashed_password, role, is_active)
                VALUES ('admin@mouraleite.com.br', 'Administrador', '{hashed_admin_password}', 'ADMIN', true)
            """))
            print("Admin criado.")

        session.commit()
    
    engine.dispose()
    print("Concluído!")

if __name__ == "__main__":
    seed_users()
