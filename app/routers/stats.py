from fastapi import APIRouter

from ..database import get_db_client
from ..schemas import DashboardStats

router = APIRouter(tags=["Statistics"])


@router.get("/stats", response_model=DashboardStats)
def get_stats():
    client = get_db_client()
    try:
        # We fetch minimal columns needed for calculation
        result = client.sqlQuery(
            "SELECT txn_type, category, amount, status FROM transactions"
        )

        tuition = 0.0
        misc = 0.0
        org = 0.0
        expenses = 0.0
        pending = 0

        collections_by_category = {}
        disbursements_by_category = {}

        def bump(map_obj, key, amt):
            map_obj[key] = map_obj.get(key, 0) + amt

        for row in result:
            txn_type = row[0]
            category = row[1] or "Uncategorized"
            # Amount is stored as integer cents in DB, convert to float
            amount = row[2] / 100.0
            status = row[3]

            if status == "Pending":
                pending += 1
                continue

            if txn_type == "Disbursement":
                expenses += amount
                bump(disbursements_by_category, category, amount)
            elif txn_type == "Collection":
                if category == "Tuition Fee":
                    tuition += amount
                elif category == "Miscellaneous Fee":
                    misc += amount
                elif category == "Organization Fund":
                    org += amount
                bump(collections_by_category, category, amount)

        return {
            "total_tuition": tuition,
            "total_misc": misc,
            "total_org": org,
            "total_expenses": expenses,
            "pending_count": pending,
            "collections_by_category": collections_by_category,
            "disbursements_by_category": disbursements_by_category,
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        # Return zeros on error so the dashboard doesn't crash completely
        return {
            "total_tuition": 0,
            "total_misc": 0,
            "total_org": 0,
            "total_expenses": 0,
            "pending_count": 0,
        }
