from app.main import app
from app.db.database import SessionLocal
from app.services.erp_integration import ErpIntegrationService
import logging

logging.basicConfig(level=logging.INFO)

def test_sync():
    db = SessionLocal()
    subdomain = "mouraleite"
    auth_string = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
    
    try:
        service = ErpIntegrationService(db, subdomain, auth_string)
        total = service.sync_realizado_income("2026-01-01", "2026-01-31")
        print(f"Total income records synced: {total}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_sync()
