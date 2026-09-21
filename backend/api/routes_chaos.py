from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from collector.fault_injector import inject, cleanup, VALID_SERVICES, ANOMALY_VALUES

router = APIRouter()

class InjectRequest(BaseModel):
    fault_type: str
    service: str = "payment-service"

@router.post("/inject")
def inject_fault(req: InjectRequest):
    """Trigger a synthetic anomaly for demo purposes."""
    if req.fault_type not in ANOMALY_VALUES:
        raise HTTPException(status_code=400, detail=f"Invalid fault_type. Options: {list(ANOMALY_VALUES.keys())}")
    if req.service not in VALID_SERVICES:
        raise HTTPException(status_code=400, detail=f"Invalid service. Options: {VALID_SERVICES}")
    
    # inject() handles falling back to db-only if k8s is missing
    inject(req.fault_type, service=req.service, db_only=False)
    return {"status": "injected", "fault_type": req.fault_type, "service": req.service}

@router.post("/cleanup")
def cleanup_faults():
    """Clear all active faults and reset state."""
    cleanup()
    return {"status": "cleaned_up"}
