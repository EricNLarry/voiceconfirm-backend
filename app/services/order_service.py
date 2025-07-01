from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import HTTPException, status

from app.models.order import OrderCreate, OrderUpdate, OrderInDB, Order, OrderStats, OrderFilters
from app.models.user import UserInDB
import logging

logger = logging.getLogger(__name__)

class OrderService:
    def __init__(self):
        pass
    
    async def create_order(self, order_data: OrderCreate, db) -> OrderInDB:
        """Create a new order."""
        try:
            # Check if order with same order_id already exists for this user
            existing_order = await db.orders.find_one({
                "order_id": order_data.order_id,
                "user_id": order_data.user_id
            })
            
            if existing_order:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Order with ID {order_data.order_id} already exists"
                )
            
            # Create order document
            order_dict = order_data.dict()
            order_dict["created_at"] = datetime.utcnow()
            order_dict["updated_at"] = datetime.utcnow()
            
            # Insert order
            result = await db.orders.insert_one(order_dict)
            order_dict["_id"] = result.inserted_id
            
            logger.info(f"Created order {order_data.order_id} for user {order_data.user_id}")
            return OrderInDB(**order_dict)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create order"
            )
    
    async def get_order(self, order_id: str, user: UserInDB, db) -> Optional[OrderInDB]:
        """Get order by ID."""
        try:
            query = {"_id": ObjectId(order_id)}
            
            # Non-admin users can only see their own orders
            if user.role != "admin":
                query["user_id"] = user.id
            
            order = await db.orders.find_one(query)
            if not order:
                return None
            
            return OrderInDB(**order)
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    async def get_orders(
        self,
        user: UserInDB,
        db,
        filters: Optional[OrderFilters] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[OrderInDB]:
        """Get orders with optional filters."""
        try:
            query = {}
            
            # Non-admin users can only see their own orders
            if user.role != "admin":
                query["user_id"] = user.id
            
            # Apply filters
            if filters:
                if filters.status:
                    query["confirmation_status"] = filters.status
                if filters.priority:
                    query["priority"] = filters.priority
                if filters.customer_name:
                    query["customer.name"] = {"$regex": filters.customer_name, "$options": "i"}
                if filters.order_id:
                    query["order_id"] = {"$regex": filters.order_id, "$options": "i"}
                if filters.date_from or filters.date_to:
                    date_query = {}
                    if filters.date_from:
                        date_query["$gte"] = filters.date_from
                    if filters.date_to:
                        date_query["$lte"] = filters.date_to
                    query["created_at"] = date_query
            
            # Execute query
            cursor = db.orders.find(query).sort("created_at", -1).skip(skip).limit(limit)
            orders = await cursor.to_list(length=limit)
            
            return [OrderInDB(**order) for order in orders]
            
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []
    
    async def update_order(self, order_id: str, order_update: OrderUpdate, user: UserInDB, db) -> Optional[OrderInDB]:
        """Update order."""
        try:
            query = {"_id": ObjectId(order_id)}
            
            # Non-admin users can only update their own orders
            if user.role != "admin":
                query["user_id"] = user.id
            
            # Check if order exists
            existing_order = await db.orders.find_one(query)
            if not existing_order:
                return None
            
            # Prepare update data
            update_data = order_update.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            
            # Special handling for status changes
            if "confirmation_status" in update_data:
                if update_data["confirmation_status"] == "confirmed":
                    update_data["confirmed_at"] = datetime.utcnow()
            
            # Update order
            await db.orders.update_one(query, {"$set": update_data})
            
            # Get updated order
            updated_order = await db.orders.find_one(query)
            logger.info(f"Updated order {order_id}")
            
            return OrderInDB(**updated_order)
            
        except Exception as e:
            logger.error(f"Failed to update order {order_id}: {e}")
            return None
    
    async def delete_order(self, order_id: str, user: UserInDB, db) -> bool:
        """Delete order."""
        try:
            query = {"_id": ObjectId(order_id)}
            
            # Non-admin users can only delete their own orders
            if user.role != "admin":
                query["user_id"] = user.id
            
            result = await db.orders.delete_one(query)
            
            if result.deleted_count > 0:
                logger.info(f"Deleted order {order_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete order {order_id}: {e}")
            return False
    
    async def get_order_stats(self, user: UserInDB, db) -> OrderStats:
        """Get order statistics."""
        try:
            query = {}
            
            # Non-admin users can only see their own stats
            if user.role != "admin":
                query["user_id"] = user.id
            
            # Aggregate statistics
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": None,
                        "total_orders": {"$sum": 1},
                        "pending_orders": {
                            "$sum": {"$cond": [{"$eq": ["$confirmation_status", "pending"]}, 1, 0]}
                        },
                        "confirmed_orders": {
                            "$sum": {"$cond": [{"$eq": ["$confirmation_status", "confirmed"]}, 1, 0]}
                        },
                        "failed_orders": {
                            "$sum": {"$cond": [{"$eq": ["$confirmation_status", "failed"]}, 1, 0]}
                        },
                        "cancelled_orders": {
                            "$sum": {"$cond": [{"$eq": ["$confirmation_status", "cancelled"]}, 1, 0]}
                        },
                        "total_call_attempts": {"$sum": "$call_attempts"},
                    }
                }
            ]
            
            result = await db.orders.aggregate(pipeline).to_list(length=1)
            
            if result:
                stats = result[0]
                total_orders = stats["total_orders"]
                confirmed_orders = stats["confirmed_orders"]
                total_call_attempts = stats["total_call_attempts"]
                
                confirmation_rate = (confirmed_orders / total_orders * 100) if total_orders > 0 else 0
                average_call_attempts = (total_call_attempts / total_orders) if total_orders > 0 else 0
                
                return OrderStats(
                    total_orders=total_orders,
                    pending_orders=stats["pending_orders"],
                    confirmed_orders=confirmed_orders,
                    failed_orders=stats["failed_orders"],
                    cancelled_orders=stats["cancelled_orders"],
                    confirmation_rate=round(confirmation_rate, 2),
                    average_call_attempts=round(average_call_attempts, 2)
                )
            else:
                return OrderStats(
                    total_orders=0,
                    pending_orders=0,
                    confirmed_orders=0,
                    failed_orders=0,
                    cancelled_orders=0,
                    confirmation_rate=0.0,
                    average_call_attempts=0.0
                )
                
        except Exception as e:
            logger.error(f"Failed to get order stats: {e}")
            return OrderStats(
                total_orders=0,
                pending_orders=0,
                confirmed_orders=0,
                failed_orders=0,
                cancelled_orders=0,
                confirmation_rate=0.0,
                average_call_attempts=0.0
            )
    
    async def bulk_import_orders(self, orders_data: List[OrderCreate], db) -> Dict[str, Any]:
        """Bulk import orders."""
        try:
            successful_imports = 0
            failed_imports = 0
            errors = []
            
            for order_data in orders_data:
                try:
                    await self.create_order(order_data, db)
                    successful_imports += 1
                except Exception as e:
                    failed_imports += 1
                    errors.append(f"Order {order_data.order_id}: {str(e)}")
            
            return {
                "successful_imports": successful_imports,
                "failed_imports": failed_imports,
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk import orders: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to bulk import orders"
            )

# Create service instance
order_service = OrderService()

