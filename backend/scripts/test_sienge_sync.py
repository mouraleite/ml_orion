import os
import sys

# Add backend dir to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.services.erp_integration import ErpIntegrationService
from app.models import user, viability, phase, revenue, construction, expenses, curves as curves_model, phase_details, snapshot, company, custom_field, cost_center, financial_plan, scenario, economic_indicator, tax_regime, actual_transaction, payment_plan, departamento
from app.models.vision import Vision, VisionNode, FinancialPlanVisionLink
from app.models import partnership as partnership_model
from app.models import migration as migration_model
import logging

logging.basicConfig(level=logging.INFO)

def test_sync():
    db = SessionLocal()
    subdomain = "mouraleite"
    auth_string = "mouraleite-contas-a-pagar:U2riBlrXuOPIpbb7TyRapoxSzaXWUisj"
    service = ErpIntegrationService(db, subdomain, auth_string)
    
    print("Testing sync for June 2026...")
    service.sync_realizado_outcome("2026-06-01", "2026-06-30")
    print("Done!")

if __name__ == "__main__":
    test_sync()
