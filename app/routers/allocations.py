from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import get_db_client
from ..routers.transactions import ensure_admin

router = APIRouter(tags=["Financial Allocations"])


class AllocationItem(BaseModel):
    id: int | None = None
    name: str
    amount: float


class AllocationResponse(BaseModel):
    items: List[AllocationItem]
    total_tuition: float


@router.get("/allocations", response_model=AllocationResponse)
def get_allocations():
    """Get all financial allocation items."""
    client = get_db_client()
    try:
        # Try to get allocations from database
        try:
            result = client.sqlQuery(
                "SELECT id, name, amount FROM financial_allocations ORDER BY id ASC"
            )
            items = []
            total = 0.0
            for row in result:
                amount = row[2] / 100.0  # Convert from cents
                items.append({
                    "id": row[0],
                    "name": row[1],
                    "amount": amount
                })
                total += amount
            
            return {
                "items": items,
                "total_tuition": total
            }
        except Exception:
            # Table doesn't exist or no data, return empty
            return {
                "items": [],
                "total_tuition": 0.0
            }
    except Exception as e:
        print(f"Get allocations error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AllocationCreateRequest(BaseModel):
    username: str
    item: AllocationItem


@router.post("/allocations", response_model=AllocationItem)
def create_allocation(req: AllocationCreateRequest):
    """Create a new allocation item. Admin only."""
    client = get_db_client()
    try:
        ensure_admin(client, req.username)
        item = req.item
        
        amount_cents = int(item.amount * 100)
        
        query = f"""
            INSERT INTO financial_allocations (name, amount)
            VALUES ('{item.name}', {amount_cents})
        """
        client.sqlExec(query)
        
        # Get the created item
        res = client.sqlQuery("SELECT id, name, amount FROM financial_allocations ORDER BY id DESC LIMIT 1")
        if not res:
            raise HTTPException(status_code=500, detail="Allocation created but could not be retrieved")
        
        return {
            "id": res[0][0],
            "name": res[0][1],
            "amount": res[0][2] / 100.0
        }
    except Exception as e:
        print(f"Create allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AllocationUpdateRequest(BaseModel):
    username: str
    item: AllocationItem


@router.put("/allocations/{item_id}", response_model=AllocationItem)
def update_allocation(item_id: int, req: AllocationUpdateRequest):
    """Update an allocation item. Admin only."""
    client = get_db_client()
    try:
        ensure_admin(client, req.username)
        item = req.item
        
        amount_cents = int(item.amount * 100)
        
        query = f"""
            UPDATE financial_allocations
            SET name = '{item.name}', amount = {amount_cents}
            WHERE id = {item_id}
        """
        client.sqlExec(query)
        
        return {
            "id": item_id,
            "name": item.name,
            "amount": item.amount
        }
    except Exception as e:
        print(f"Update allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AllocationDeleteRequest(BaseModel):
    username: str


@router.delete("/allocations/{item_id}")
def delete_allocation(item_id: int, username: str):
    """Delete an allocation item. Admin only."""
    client = get_db_client()
    try:
        ensure_admin(client, username)
        
        client.sqlExec(f"DELETE FROM financial_allocations WHERE id = {item_id}")
        
        return {"message": "Allocation deleted successfully"}
    except Exception as e:
        print(f"Delete allocation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
