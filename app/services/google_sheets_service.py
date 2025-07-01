import asyncio
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    def __init__(self):
        self.service = None
        self.credentials = None
        
    async def initialize_service(self, credentials_json: str = None, service_account_json: str = None):
        """Initialize Google Sheets service with credentials"""
        try:
            if service_account_json:
                # Use service account credentials
                credentials_info = json.loads(service_account_json)
                self.credentials = service_account.Credentials.from_service_account_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            elif credentials_json:
                # Use OAuth2 credentials
                credentials_info = json.loads(credentials_json)
                self.credentials = Credentials.from_authorized_user_info(
                    credentials_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                raise ValueError("No credentials provided")
                
            self.service = build('sheets', 'v4', credentials=self.credentials)
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            return False
    
    async def create_spreadsheet(self, title: str) -> Optional[Dict[str, Any]]:
        """Create a new spreadsheet"""
        try:
            spreadsheet = {
                'properties': {
                    'title': title
                },
                'sheets': [{
                    'properties': {
                        'title': 'Orders',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 20
                        }
                    }
                }]
            }
            
            result = self.service.spreadsheets().create(body=spreadsheet).execute()
            
            # Set up headers
            await self.setup_order_headers(result['spreadsheetId'])
            
            return result
            
        except HttpError as e:
            logger.error(f"Failed to create spreadsheet: {str(e)}")
            return None
    
    async def setup_order_headers(self, spreadsheet_id: str):
        """Set up headers for the orders sheet"""
        headers = [
            'Order ID', 'Customer Name', 'Customer Phone', 'Customer Email',
            'Product Name', 'Quantity', 'Total Amount', 'Order Date',
            'Status', 'Call Status', 'Call Attempts', 'Last Call Date',
            'Confirmation Response', 'Notes', 'Created At', 'Updated At'
        ]
        
        try:
            body = {
                'values': [headers]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Orders!A1:P1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Format headers
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': len(headers)
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.2,
                                'green': 0.4,
                                'blue': 0.8
                            },
                            'textFormat': {
                                'foregroundColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 1.0
                                },
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
            
            body = {'requests': requests}
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
        except HttpError as e:
            logger.error(f"Failed to setup headers: {str(e)}")
    
    async def add_order(self, spreadsheet_id: str, order_data: Dict[str, Any]) -> bool:
        """Add a new order to the spreadsheet"""
        try:
            # Get current data to find next row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Orders!A:A'
            ).execute()
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Prepare order data
            row_data = [
                order_data.get('order_id', ''),
                order_data.get('customer_name', ''),
                order_data.get('customer_phone', ''),
                order_data.get('customer_email', ''),
                order_data.get('product_name', ''),
                order_data.get('quantity', ''),
                order_data.get('total_amount', ''),
                order_data.get('order_date', ''),
                order_data.get('status', 'pending'),
                order_data.get('call_status', 'not_called'),
                order_data.get('call_attempts', 0),
                order_data.get('last_call_date', ''),
                order_data.get('confirmation_response', ''),
                order_data.get('notes', ''),
                order_data.get('created_at', ''),
                order_data.get('updated_at', '')
            ]
            
            body = {
                'values': [row_data]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'Orders!A{next_row}:P{next_row}',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f"Failed to add order: {str(e)}")
            return False
    
    async def update_order_status(self, spreadsheet_id: str, order_id: str, 
                                 call_status: str, confirmation_response: str = '',
                                 notes: str = '') -> bool:
        """Update order call status and response"""
        try:
            # Find the order row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Orders!A:P'
            ).execute()
            
            values = result.get('values', [])
            
            for i, row in enumerate(values):
                if len(row) > 0 and row[0] == order_id:
                    # Update the row
                    row_num = i + 1
                    
                    # Update call status (column J), confirmation response (column M), notes (column N)
                    updates = []
                    
                    if call_status:
                        updates.append({
                            'range': f'Orders!J{row_num}',
                            'values': [[call_status]]
                        })
                    
                    if confirmation_response:
                        updates.append({
                            'range': f'Orders!M{row_num}',
                            'values': [[confirmation_response]]
                        })
                    
                    if notes:
                        updates.append({
                            'range': f'Orders!N{row_num}',
                            'values': [[notes]]
                        })
                    
                    # Update call attempts and last call date
                    current_attempts = int(row[10]) if len(row) > 10 and row[10].isdigit() else 0
                    updates.append({
                        'range': f'Orders!K{row_num}',
                        'values': [[current_attempts + 1]]
                    })
                    
                    from datetime import datetime
                    updates.append({
                        'range': f'Orders!L{row_num}',
                        'values': [[datetime.now().isoformat()]]
                    })
                    
                    # Batch update
                    body = {
                        'valueInputOption': 'RAW',
                        'data': updates
                    }
                    
                    self.service.spreadsheets().values().batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body=body
                    ).execute()
                    
                    return True
            
            return False
            
        except HttpError as e:
            logger.error(f"Failed to update order status: {str(e)}")
            return False
    
    async def get_pending_orders(self, spreadsheet_id: str) -> List[Dict[str, Any]]:
        """Get all pending orders from the spreadsheet"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range='Orders!A2:P'  # Skip header row
            ).execute()
            
            values = result.get('values', [])
            orders = []
            
            for row in values:
                if len(row) >= 9 and row[9] in ['not_called', 'failed']:  # Call status column
                    order = {
                        'order_id': row[0] if len(row) > 0 else '',
                        'customer_name': row[1] if len(row) > 1 else '',
                        'customer_phone': row[2] if len(row) > 2 else '',
                        'customer_email': row[3] if len(row) > 3 else '',
                        'product_name': row[4] if len(row) > 4 else '',
                        'quantity': row[5] if len(row) > 5 else '',
                        'total_amount': row[6] if len(row) > 6 else '',
                        'order_date': row[7] if len(row) > 7 else '',
                        'status': row[8] if len(row) > 8 else '',
                        'call_status': row[9] if len(row) > 9 else '',
                        'call_attempts': int(row[10]) if len(row) > 10 and row[10].isdigit() else 0,
                        'last_call_date': row[11] if len(row) > 11 else '',
                        'confirmation_response': row[12] if len(row) > 12 else '',
                        'notes': row[13] if len(row) > 13 else '',
                        'created_at': row[14] if len(row) > 14 else '',
                        'updated_at': row[15] if len(row) > 15 else ''
                    }
                    orders.append(order)
            
            return orders
            
        except HttpError as e:
            logger.error(f"Failed to get pending orders: {str(e)}")
            return []
    
    async def get_spreadsheet_info(self, spreadsheet_id: str) -> Optional[Dict[str, Any]]:
        """Get spreadsheet information"""
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            return {
                'id': result['spreadsheetId'],
                'title': result['properties']['title'],
                'url': result['spreadsheetUrl'],
                'sheets': [sheet['properties']['title'] for sheet in result['sheets']]
            }
            
        except HttpError as e:
            logger.error(f"Failed to get spreadsheet info: {str(e)}")
            return None

# Global instance
google_sheets_service = GoogleSheetsService()

