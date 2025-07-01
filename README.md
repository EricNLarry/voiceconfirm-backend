# VoiceConfirm Backend

FastAPI-based backend for the VoiceConfirm SaaS platform that automates order confirmation calls using AI voice technology.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **MongoDB Database**: Document-based database for flexible data storage
- **JWT Authentication**: Secure token-based authentication
- **ElevenLabs Integration**: AI-powered voice synthesis and conversation
- **Twilio Integration**: Voice calls and WhatsApp messaging
- **Role-based Access Control**: Admin and user roles
- **Comprehensive API**: RESTful endpoints for all operations
- **Cloud Run Ready**: Optimized for Google Cloud Run deployment

## Quick Start

### Prerequisites

- Python 3.11+
- MongoDB (Atlas recommended for production)
- Redis (optional, for caching)

### Local Development

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment variables:
```bash
cp .env.example .env
```

4. Configure your `.env` file with your API keys and database settings

5. Run the application:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## Environment Variables

Configure the following environment variables in your `.env` file:

### Database
- `MONGODB_URL`: MongoDB connection string (use MongoDB Atlas for production)
- `DATABASE_NAME`: Database name (default: voiceconfirm)

### Authentication
- `SECRET_KEY`: JWT secret key (generate a secure random string)
- `ALGORITHM`: JWT algorithm (default: HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Token expiration time (default: 30)

### ElevenLabs API
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key

### Twilio (for Voice calls)
- `TWILIO_ACCOUNT_SID`: Twilio Account SID
- `TWILIO_AUTH_TOKEN`: Twilio Auth Token
- `TWILIO_PHONE_NUMBER`: Twilio phone number for making calls

### Stripe (for payments)
- `STRIPE_SECRET_KEY`: Stripe secret key
- `STRIPE_PUBLISHABLE_KEY`: Stripe publishable key
- `STRIPE_WEBHOOK_SECRET`: Stripe webhook secret

### Other
- `REDIS_URL`: Redis connection string (optional)
- `FRONTEND_URL`: Frontend application URL for CORS
- `ENVIRONMENT`: Environment (development/production)

## Google Cloud Run Deployment

### Prerequisites
- Google Cloud account with billing enabled
- Google Cloud CLI installed and configured
- MongoDB Atlas database (recommended)

### Deployment Steps

1. **Prepare your environment variables**:
   - Create a `.env` file with production values
   - Use MongoDB Atlas for the database
   - Set `ENVIRONMENT=production`

2. **Deploy to Cloud Run**:
```bash
# Build and deploy
gcloud run deploy voiceconfirm-backend \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --env-vars-file .env
```

3. **Configure custom domain** (optional):
```bash
gcloud run domain-mappings create \
  --service voiceconfirm-backend \
  --domain api.yourdomain.com \
  --region us-central1
```

### Environment Variables for Cloud Run

Set these in Google Cloud Console or via CLI:

```bash
gcloud run services update voiceconfirm-backend \
  --set-env-vars="MONGODB_URL=your_mongodb_atlas_url,SECRET_KEY=your_secret_key,ELEVENLABS_API_KEY=your_elevenlabs_key" \
  --region us-central1
```

## API Documentation

Once deployed, access the API documentation at:
- **Swagger UI**: `https://your-service-url/docs`
- **ReDoc**: `https://your-service-url/redoc`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout user

### Orders
- `GET /api/orders` - Get orders with filters
- `POST /api/orders` - Create new order
- `GET /api/orders/{id}` - Get order by ID
- `PUT /api/orders/{id}` - Update order
- `DELETE /api/orders/{id}` - Delete order
- `GET /api/orders/stats` - Get order statistics
- `POST /api/orders/bulk-import` - Bulk import orders

### Calls
- `GET /api/calls` - Get calls with filters
- `POST /api/calls/{order_id}/initiate` - Initiate order confirmation call
- `GET /api/calls/{id}` - Get call by ID
- `GET /api/calls/stats` - Get call statistics
- `GET /api/calls/voices/available` - Get available voices
- `GET /api/calls/languages/supported` - Get supported languages
- `POST /api/calls/webhook/twilio` - Twilio webhook endpoint

## Database Schema

### Users Collection
- User authentication and profile information
- Subscription details
- Settings and preferences

### Orders Collection
- Order details from e-commerce platforms
- Customer information
- Confirmation status and call attempts

### Call Logs Collection
- Call records and outcomes
- Audio transcripts and recordings
- Performance metrics

## Security

- JWT tokens for authentication
- Password hashing with bcrypt
- CORS configuration
- Input validation with Pydantic
- Environment variable protection
- Rate limiting (implement as needed)

## Monitoring

- Health check endpoint: `/health`
- Structured logging
- Error tracking
- Performance metrics

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/
isort app/
```

### Type Checking
```bash
mypy app/
```

## Production Considerations

1. **Database**: Use MongoDB Atlas for production
2. **Secrets**: Store sensitive data in Google Secret Manager
3. **Monitoring**: Set up Cloud Monitoring and Logging
4. **Scaling**: Configure Cloud Run autoscaling
5. **Security**: Enable Cloud Armor for DDoS protection
6. **Backup**: Set up automated database backups

## Support

For support and questions, please contact the development team.

## License

This project is licensed under the MIT License.

## Author

Built by Affan Hashmi

