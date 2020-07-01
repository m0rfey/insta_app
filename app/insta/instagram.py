import base64
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timedelta

import simplejson
from django.conf import settings
from urllib.parse import urlencode, quote_plus

from django.utils.timezone import get_current_timezone
from django_redis import get_redis_connection
from httplib2 import Http
from .models import InstagramAccount


class API:
    __redis_key = 'instagram:users:%s:'
    AUTHORIZATION_URL = 'https://api.instagram.com/oauth/authorize'
    ACCESS_TOKEN_URL = 'https://api.instagram.com/oauth/access_token'
    GRAPH_URL = 'https://graph.instagram.com/'

    def __init__(self):
        self.model = InstagramAccount
        self.redis = get_redis_connection(alias='instagram')

    def auth_headers(self):
        return {'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'}

    def set_user_cache(self, user_id):
        unique_id = uuid.uuid4().hex
        self.redis.set(self.__redis_key % unique_id, str(user_id), 60)
        return unique_id

    def get_user_cache(self, unique_id):
        user_id = self.redis.get(self.__redis_key % unique_id)
        return int(user_id) if user_id else user_id

    def get_authorize_uri(self, user_id):
        unique_id = self.set_user_cache(user_id)
        params = {
            'client_id': settings.INSTAGRAM_CONFIG['client_id'],
            'redirect_uri': 'https://tornadogame.club/complete/instagram/',
            'scope': 'user_profile,user_media',
            'response_type': 'code',
            'state': unique_id
        }
        uri = self.AUTHORIZATION_URL + '?' + urlencode(params, quote_via=quote_plus)
        return uri

    def get_json(self, url, body=None, *args, method='GET', **kwargs):
        http_object = Http(disable_ssl_certificate_validation=True)
        response, content = http_object.request(url, method=method, body=body, headers=self.auth_headers())
        parsed = simplejson.loads(content.decode())
        if int(response['status']) != 200:
            raise ValueError(parsed.get("error_message", ""))
        return parsed

    def exchange_long_live_token(self, token):
        """Exchange a short-lived Instagram User Access Token for a long-lived Instagram User Access Token."""
        params = urlencode({
            'grant_type': 'ig_exchange_token',
            'client_secret': settings.INSTAGRAM_CONFIG['client_secret'],
            'access_token': token
        })
        uri = f'{self.GRAPH_URL}/access_token?{params}'
        response = self.get_json(uri)
        return response

    def exchange_code_for_token(self, code, user):
        data = urlencode({
            'client_id': settings.INSTAGRAM_CONFIG['client_id'],
            'client_secret': settings.INSTAGRAM_CONFIG['client_secret'],
            'redirect_uri': 'https://tornadogame.club/complete/instagram/',
            'grant_type': 'authorization_code',
            'code': code,
        })
        response = self.get_json(self.ACCESS_TOKEN_URL, body=data, method='POST')
        long_live_token = self.exchange_long_live_token(response['access_token'])
        return self.create(
            user=user,
            access_token=long_live_token['access_token'],
            token_type=long_live_token['token_type'],
            expires_in=long_live_token['expires_in'],
            data=self.get_user(response['user_id'], long_live_token['access_token'])
        )

    def get_user(self, user_id, token):
        uri = self.GRAPH_URL + f'{user_id}?fields=id,username&access_token={token}'
        response = self.get_json(uri)
        return response

    def get_user_media(self, user_id, token):
        uri = self.GRAPH_URL + f'{user_id}/media?access_token={token}'
        response = self.get_json(uri)
        data = [int(row['id']) for row in response['data']]
        return data

    def get_media_fields(self, media_id, token):
        """Get fields and edges on an image, video, or album."""
        fields = ['id', 'media_type', 'media_url', 'permalink', 'thumbnail_url', 'timestamp', 'username']
        uri = self.GRAPH_URL + f'{media_id}/?fields={",".join(fields)}&access_token={token}'
        response = self.get_json(uri)
        return response

    def __get_account_params(self, user, access_token, token_type, expires_in, **kwargs):
        tz = get_current_timezone()
        return {
            'user_id': user.id,
            'access_token': access_token,
            'token_type': token_type,
            'expires_in': datetime.now(tz=tz) + timedelta(seconds=expires_in),
            'data': kwargs.get('data', {})
        }

    def refresh_access_token(self, token, user):
        uri = self.GRAPH_URL + f'refresh_access_token?grant_type=ig_refresh_token&access_token={token}'
        response = self.get_json(uri)
        return self.update(
            user=user,
            access_token=response['access_token'],
            token_type=response['token_type'],
            expires_in=response['expires_in'],
            data=self.get_user(response['user_id'], response['access_token'])
        )

    def get_insta_account(self, user, code=None):
        try:
            account = self.model.objects.get(user_id=user.id)
            if not account.is_not_expired():
                account = self.refresh_access_token(account.access_token, user)
        except self.model.DoesNotExist:
            account = self.exchange_code_for_token(code, user)
        return account

    def create(self, **kwargs):
        params = self.__get_account_params(**kwargs)
        account = self.model(**params)
        account.save()
        return account

    def update(self, **kwargs):
        params = self.__get_account_params(**kwargs)
        user_id = params.pop('user_id')
        return self.model.objects.filter(user_id=user_id).update(**params)

    def parse_signed_request(self, signed_request):
        encoded_sign, payload = signed_request.split('.', 2)
        # client_secret = settings.INSTAGRAM_CONFIG['client_secret']
        # sig = base64.urlsafe_b64decode(encoded_sign + '=' * (4 - len(encoded_sign) % 4))
        params = base64.urlsafe_b64decode(payload + '=' * (4 - len(payload) % 4))
        data = json.loads(params)
        # expected_sig = hmac.new(client_secret.encode(), params, 'sha256').digest()
        # if not hmac.compare_digest(sig, expected_sig):
        #     pass
        return data

    def destroy(self, signed_request: str):
        data = self.parse_signed_request(signed_request)
        try:
            account = self.model.objects.get(data__id=data['user_id'])
            account.delete()
        except self.model.DoesNotExist as e:
            pass
