
from authlib.integrations.httpx_client import AsyncOAuth2Client
from quart import request, render_template, jsonify, redirect, session, url_for, Blueprint
from dotenv import load_dotenv
import os
import re
import json

from db.models import session as db_sesh, User

load_dotenv()

CLIENT_ID = os.getenv('DISCORD_BOT_CLIENT_ID')
CLIENT_SECRET = os.getenv('DISCORD_BOT_CLIENT_SECRET')
REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI')

def create_discord_oauth(bot):

    discord_login = Blueprint('discord', __name__)

    @discord_login.route('/login/discord')
    async def discord_signin():
        discord_oauth = AsyncOAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_endpoint='https://discord.com/api/oauth2/token',
            authorization_endpoint='https://discord.com/api/oauth2/authorize',
            redirect_uri=REDIRECT_URI,
            client_kwargs={'scope': 'identify'},
            scope="identify"
        )
        authorization_url, state = discord_oauth.create_authorization_url('https://discord.com/api/oauth2/authorize')
        # Store the state in session or a secure place
        session['oauth_state'] = state
        return redirect(authorization_url)


    @discord_login.route('/auth/callback')
    async def authorize():
        print(request.args)
        code = request.args.get('code')  # Retrieve the authorization code
        print(request)
        discord_oauth = AsyncOAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_endpoint='https://discord.com/api/oauth2/token',
            authorization_endpoint='https://discord.com/api/oauth2/authorize',
            redirect_uri=REDIRECT_URI
        )

        # Ensure the correct code is used in the token exchange
        token = await discord_oauth.fetch_token(
            authorization_response=request.url
        )
        session['token'] = token
        user = await discord_oauth.get('https://discord.com/api/users/@me')
        session['user'] = user.json()
        print(f"User: {session['user']}")
        user = db_sesh.query(User).filter(User.discord_id == session['user']['id']).first()
        if not user:
            user = User(discord_id=session['user']['id'],
                        username=user['username'],
                        patreon=False)
        return redirect(url_for('frontend.homepage'))
    
    return discord_login