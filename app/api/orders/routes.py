from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.models.order import OrderCreate, OrderUpdate, Order, OrderStats, OrderFilters
from app.models.user import UserInDB
from app.services.auth_service import auth_service
from app.services.order_service import order_service
from app.db.database import get_db

router = APIRouter()

@router.post("/", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Create a new order."""
    order_data.user_id = current_user.id
    order = await order_service.create_order(order_data, db)
    return Order(**order.dict())

@router.get("/", response_model=List[Order])
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    customer_name: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None),
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Get orders with optional filters."""
    filters = OrderFilters(
        status=status,
        priority=priority,
        customer_name=customer_name,
        order_id=order_id
    )
    
    orders = await order_service.get_orders(current_user, db, filters, skip, limit)
    return [Order(**order.dict()) for order in orders]

@router.get("/stats", response_model=OrderStats)
async def get_order_stats(
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Get order statistics."""
    stats = await order_service.get_order_stats(current_user, db)
    return stats

@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: str,
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Get order by ID."""
    order = await order_service.get_order(order_id, current_user, db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return Order(**order.dict())

@router.put("/{order_id}", response_model=Order)
async def update_order(
    order_id: str,
    order_update: OrderUpdate,
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Update order."""
    order = await order_service.update_order(order_id, order_update, current_user, db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return Order(**order.dict())

@router.delete("/{order_id}")
async def delete_order(
    order_id: str,
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Delete order."""
    success = await order_service.delete_order(order_id, current_user, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    return {"message": "Order deleted successfully"}

@router.post("/bulk-import")
async def bulk_import_orders(
    orders_data: List[OrderCreate],
    current_user: UserInDB = Depends(auth_service.get_current_active_user),
    db = Depends(get_db)
):
    """Bulk import orders."""
    # Set user_id for all orders
    for order_data in orders_data:
        order_data.user_id = current_user.id
    
    result = await order_service.bulk_import_orders(orders_data, db)
    return result

