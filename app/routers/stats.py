from fastapi import APIRouter, HTTPException
from ..schemas import DashboardStats
from ..database import get_db_client

router = APIRouter(tags=["Statistics"])

@router.get("/stats", response_model=DashboardStats)
def get_stats():
    client = get_db_client()
    try:
        result = client.sqlQuery("SELECT txn_type, category, amount FROM transactions")
        
        tuition = 0
        misc = 0
        org = 0
        expenses = 0
        
        for row in result:
            txn_type = row[0]
            category = row[1]
            amount = row[2] / 100.0
            
            if txn_type == 'Disbursement':
                expenses += amount
            elif txn_type == 'Collection':
                if category == 'Tuition Fee': tuition += amount
                elif category == 'Miscellaneous Fee': misc += amount
                elif category == 'Organization Fund': org += amount

        return {
            "total_tuition": tuition,
            "total_misc": misc,
            "total_org": org,
            "total_expenses": expenses
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
