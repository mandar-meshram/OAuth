from fastapi import APIRouter, Request, Depends
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from jwt_utils import create_jwt_token
import os
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

router = APIRouter()

# OAuth config - use environment variavles
config = Config()

# Verify that environment variables are set
google_client_id = os.getenv('GOOGLE_CLIENT_ID')
google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

if not google_client_id or not google_client_secret or google_client_id == "your-google-client-id":
    print('Warning : GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET not found or using placeholder values')
    print('OAuth functionality will be disabled. Please set real Google OAuth credentials.')
    oauth = None
else:
    print(f'Google OAuth configured with Client ID : {google_client_id[:10]}...')
    oauth = OAuth(config)
    oauth.register(
        name='google',
        client_id=google_client_id,
        client_secret=google_client_secret,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope':'openid email profile',
            'response_type':'code',
            'access_type':'offline',
            'prompt':'select_account'
        }
    )

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/login/google")
async def login_via_google(request : Request):
    if not oauth:
        return HTMLResponse(
            content='''
<h1>OAuth Not Configured</h1>
<p>Google OAuth is not configured, Please:</p>
<ol>
<li>Go to <a href="https://console.cloud.google.com/">Google Cloud Console</a></li>
<li>Create OAUth 2.0 credentials</li>
<li>Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file</li>
<li>Add http://localhost:8000/auth/callback as redirect URL</li>
</ol>
<a href="/>Back to Login</a>
''',
            status_code=500
        )
    # Use the same scheme and host as the incoming request
    base_url = f'{request.url.scheme}://{request.url.netloc}'
    redirect_url = f'{base_url}/auth/callback'

    print(f'DEBUG: Using redirect_url: {redirect_url}')
    print(f'DEBUG: Session data before redirect: {request.session}')

    try:
        # Clear any existing session data that might interfere
        if hasattr(request, 'session'):
            request.session.clear()

        return await oauth.google.authorize_redirect(request, redirect_url)
    except Exception as e:
        print(f'DEBUG: Error in authorize_redirect: {e}')
        return HTMLResponse(
            content=f'<h1>OAuth Error</h1><p>Error initiating OAuth: {str(e)}</p><a href="/">Back to login</a>',
            status_code=500
        )

@router.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    if not oauth:
        return HTMLResponse(
            content='<h1>OAuth Error</h1><p>Google OAuth is not configured.</p>',
            status_code=500
        )
    print(f'DEBUG: Callback received')
    print(f'DEBUG: Request URL: {request.url}')
    print(f'DEBUG: Query params: {dict(request.query_params)}')

    try:
        # get authorization token
        token = await oauth.google.authorize_access_token(request)
        print(f'DEBUG: Token received: {token.keys() if token else 'No token'}')

        # Try to get user info from ID token first
        user_info = None
        if 'id_token' in token:
            try:
                user_info = await oauth.google.parse_id_token(request, token)
                print(f'DEBUG: Got user info from ID token: {user_info.get('email','no email')}')
            except Exception as e:
                print(f'DEBUG: Failed to parse ID token: {e}')

        # If no ID token or parsing failed, get user info from userinfo endpoint
        if not user_info:
            print('DEBUG: Fetching user info from userinfo endpoint')
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v2/userinfo', token=token)
            user_info = resp.json()
            print(f'DEBUG: Got user info from userinfo: {user_info.get('email','no email')}')

        if not user_info or 'email' not in user_info:
            raise Exception('Could not get user email from Google')
            
        # Check if user exists in database
        existing_user = db.query(User).filter(User.username == user_info['email']).first()

        if not existing_user:
            # Create new user if not exists
            new_user = User(
                username=user_info['email'],
                hashed_password='',  # No password needed for OAuth users
                role='user'  # Default role
            )
            db.add(new_user)
            db.commit()
            existing_user = new_user
            print(f'DEBUG: Created new user: {user_info['email']}')
        else:
            print(f'DEBUG: Found existing user: {user_info['email']}')

        # Create JWT token for the user
        jwt_token = create_jwt_token(existing_user.username, existing_user.role)

        # Get user name, fallback to email if not available
        username = user_info.get('name', user_info.get('email', 'User'))

        # Redirect to welcome page with username
        response = RedirectResponse(
            url=f'/welcome?username={username}',
            status_code=302
        )
        response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=True,  # Set to True in production with HTTPS
        samesite="lax"
        )
        return response
    except Exception as e:
        print(f"DEBUG: Error in callback: {str(e)}")
        print(f"DEBUG: Error type: {type(e)}")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        
        # Handle OAuth errors
        return HTMLResponse(
            content=f"""
            <h1>Authentication Error</h1>
            <p>Error: {str(e)}</p>
            <p>Please try again or contact support if this persists.</p>
            <a href='/'>← Back to Login</a>
            """,
            status_code=400
        )
