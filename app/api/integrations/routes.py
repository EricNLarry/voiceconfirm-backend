from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from app.models.google_sheets import (
    GoogleSheetsSetup, 
    GoogleSheetsResponse, 
    OrderImport, 
    OrderUpdate,
    GoogleSheetsIntegration
)
from app.models.user import User
from app.services.auth_service import get_current_user
from app.services.google_sheets_service import google_sheets_service
from app.db.database import get_database
from datetime import datetime
import json

router = APIRouter()

@router.post("/google-sheets/setup", response_model=GoogleSheetsResponse)
async def setup_google_sheets(
    setup_data: GoogleSheetsSetup,
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """Set up Google Sheets integration"""
    try:
        # Initialize Google Sheets service
        if setup_data.credentials_type == "service_account":
            success = await google_sheets_service.initialize_service(
                service_account_json=setup_data.credentials_data
            )
        else:
            success = await google_sheets_service.initialize_service(
                credentials_json=setup_data.credentials_data
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to initialize Google Sheets service with provided credentials"
            )
        
        spreadsheet_id = setup_data.existing_spreadsheet_id
        spreadsheet_info = None
        
        if not spreadsheet_id:
            # Create new spreadsheet
            result = await google_sheets_service.create_spreadsheet(setup_data.spreadsheet_title)
            if not result:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create new spreadsheet"
                )
            spreadsheet_id = result['spreadsheetId']
            spreadsheet_info = {
                'id': result['spreadsheetId'],
                'title': result['properties']['title'],
                'url': result['spreadsheetUrl']
            }
        else:
            # Get existing spreadsheet info
            spreadsheet_info = await google_sheets_service.get_spreadsheet_info(spreadsheet_id)
            if not spreadsheet_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Spreadsheet not found or access denied"
                )
        
        # Save integration to database
        integration_data = {
            "user_id": str(current_user.id),
            "spreadsheet_id": spreadsheet_id,
            "spreadsheet_title": spreadsheet_info['title'],
            "spreadsheet_url": spreadsheet_info['url'],
            "credentials_type": setup_data.credentials_type,
            "credentials_data": setup_data.credentials_data,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Remove existing integration for this user
        await db.google_sheets_integrations.delete_many({"user_id": str(current_user.id)})
        
        # Insert new integration
        result = await db.google_sheets_integrations.insert_one(integration_data)
        
        return GoogleSheetsResponse(
            success=True,
            message="Google Sheets integration set up successfully",
            spreadsheet_id=spreadsheet_id,
            spreadsheet_url=spreadsheet_info['url'],
            data=spreadsheet_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set up Google Sheets integration: {str(e)}"
        )

@router.get("/google-sheets/status", response_model=GoogleSheetsResponse)
async def get_google_sheets_status(
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get current Google Sheets integration status"""
    try:
        integration = await db.google_sheets_integrations.find_one(
            {"user_id": str(current_user.id), "is_active": True}
        )
        
        if not integration:
            return GoogleSheetsResponse(
                success=False,
                message="No active Google Sheets integration found"
            )
        
        return GoogleSheetsResponse(
            success=True,
            message="Google Sheets integration is active",
            spreadsheet_id=integration['spreadsheet_id'],
            spreadsheet_url=integration['spreadsheet_url'],
            data={
                'title': integration['spreadsheet_title'],
                'created_at': integration['created_at'].isoformat(),
                'credentials_type': integration['credentials_type']
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integration status: {str(e)}"
        )

@router.post("/google-sheets/import-order", response_model=GoogleSheetsResponse)
async def import_order_to_sheets(
    order_data: OrderImport,
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """Import a single order to Google Sheets"""
    try:
        # Get user's integration
        integration = await db.google_sheets_integrations.find_one(
            {"user_id": str(current_user.id), "is_active": True}
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google Sheets integration found"
            )
        
        # Initialize service with stored credentials
        if integration['credentials_type'] == "service_account":
            success = await google_sheets_service.initialize_service(
                service_account_json=integration['credentials_data']
            )
        else:
            success = await google_sheets_service.initialize_service(
                credentials_json=integration['credentials_data']
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize Google Sheets service"
            )
        
        # Prepare order data for sheets
        sheets_order_data = {
            'order_id': order_data.order_id,
            'customer_name': order_data.customer_name,
            'customer_phone': order_data.customer_phone,
            'customer_email': order_data.customer_email or '',
            'product_name': order_data.product_name,
            'quantity': str(order_data.quantity),
            'total_amount': str(order_data.total_amount),
            'order_date': order_data.order_date or datetime.now().strftime('%Y-%m-%d'),
            'status': 'pending',
            'call_status': 'not_called',
            'call_attempts': 0,
            'last_call_date': '',
            'confirmation_response': '',
            'notes': order_data.notes or '',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # Add order to sheets
        success = await google_sheets_service.add_order(
            integration['spreadsheet_id'],
            sheets_order_data
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add order to Google Sheets"
            )
        
        return GoogleSheetsResponse(
            success=True,
            message="Order imported to Google Sheets successfully",
            spreadsheet_id=integration['spreadsheet_id'],
            spreadsheet_url=integration['spreadsheet_url']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import order: {str(e)}"
        )

@router.post("/google-sheets/update-order", response_model=GoogleSheetsResponse)
async def update_order_in_sheets(
    order_update: OrderUpdate,
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """Update order status in Google Sheets"""
    try:
        # Get user's integration
        integration = await db.google_sheets_integrations.find_one(
            {"user_id": str(current_user.id), "is_active": True}
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google Sheets integration found"
            )
        
        # Initialize service with stored credentials
        if integration['credentials_type'] == "service_account":
            success = await google_sheets_service.initialize_service(
                service_account_json=integration['credentials_data']
            )
        else:
            success = await google_sheets_service.initialize_service(
                credentials_json=integration['credentials_data']
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize Google Sheets service"
            )
        
        # Update order in sheets
        success = await google_sheets_service.update_order_status(
            integration['spreadsheet_id'],
            order_update.order_id,
            order_update.call_status,
            order_update.confirmation_response or '',
            order_update.notes or ''
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found in Google Sheets"
            )
        
        return GoogleSheetsResponse(
            success=True,
            message="Order updated in Google Sheets successfully",
            spreadsheet_id=integration['spreadsheet_id'],
            spreadsheet_url=integration['spreadsheet_url']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order: {str(e)}"
        )

@router.get("/google-sheets/pending-orders")
async def get_pending_orders_from_sheets(
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get pending orders from Google Sheets"""
    try:
        # Get user's integration
        integration = await db.google_sheets_integrations.find_one(
            {"user_id": str(current_user.id), "is_active": True}
        )
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google Sheets integration found"
            )
        
        # Initialize service with stored credentials
        if integration['credentials_type'] == "service_account":
            success = await google_sheets_service.initialize_service(
                service_account_json=integration['credentials_data']
            )
        else:
            success = await google_sheets_service.initialize_service(
                credentials_json=integration['credentials_data']
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initialize Google Sheets service"
            )
        
        # Get pending orders
        orders = await google_sheets_service.get_pending_orders(
            integration['spreadsheet_id']
        )
        
        return {
            "success": True,
            "message": f"Retrieved {len(orders)} pending orders",
            "orders": orders,
            "spreadsheet_url": integration['spreadsheet_url']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending orders: {str(e)}"
        )

@router.delete("/google-sheets/disconnect", response_model=GoogleSheetsResponse)
async def disconnect_google_sheets(
    current_user: User = Depends(get_current_user),
    db = Depends(get_database)
):
    """Disconnect Google Sheets integration"""
    try:
        result = await db.google_sheets_integrations.update_one(
            {"user_id": str(current_user.id)},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active Google Sheets integration found"
            )
        
        return GoogleSheetsResponse(
            success=True,
            message="Google Sheets integration disconnected successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect integration: {str(e)}"
        )

