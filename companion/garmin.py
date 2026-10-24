"""Adapter over Garmin's official read-only client; credentials never leave Garmin."""
import logging
import os
import time
from pathlib import Path

KEY_FILE = Path.home() / '.config/garmin/connect-personal-api-key'
TOKEN_FILE = Path.home() / '.config/garmin/connect-personal-api-bearer-token.json'
BASE = 'https://personal.connectapi.garmin.com'

class SafeError(Exception):
    """Contains only user-safe messages, never remote bodies, headers, or secrets."""
    def __init__(self, message, status=None):
        super().__init__(message); self.status=status

class Garmin:
    def __init__(self):
        from garmin_personal_api import PersonalApiAuthenticator, GarminPersonalApiClient, resolve_api_key
        from garmin_personal_api.constants import BASE_URL_ENV_VAR
        # Disallow the official client's environment-based alternate host override.
        if os.environ.get(BASE_URL_ENV_VAR, BASE).rstrip('/') != BASE:
            raise SafeError('An alternate Garmin server was configured. Remove that override; only Garmin’s official server is allowed.')
        logging.getLogger('garmin_personal_api').disabled=True
        KEY_FILE.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        KEY_FILE.parent.chmod(0o700)
        if not KEY_FILE.is_file() or KEY_FILE.is_symlink():
            raise SafeError('Your local Garmin key is missing. Double-click Setup Garmin Dashboard.command first.')
        KEY_FILE.chmod(0o600)
        if TOKEN_FILE.is_symlink():raise SafeError('The local token cache is a symbolic link. Remove that link before refreshing.')
        if TOKEN_FILE.exists(): TOKEN_FILE.chmod(0o600)
        try:
            self.key=resolve_api_key(key_file=KEY_FILE)
            self.auth=PersonalApiAuthenticator(bearer_token_cache_file=TOKEN_FILE)
            self.client=GarminPersonalApiClient(self.auth.obtain_token(self.key).access_token)
        except Exception as e:
            raise safe_error(e) from None
        self.client.base_url=BASE
        self.auth.base_url=BASE
    def call(self, method, *args, **kwargs):
        from garmin_personal_api import HttpError
        refreshed=False
        for attempt in range(5):
            try:
                # Checks expiry before every request, including a long historical import.
                self.client.update_bearer_token(self.auth.obtain_token(self.key).access_token)
                return getattr(self.client,method)(*args,**kwargs)
            except HttpError as e:
                if e.status_code==401 and not refreshed:
                    try: self.client.update_bearer_token(self.auth.obtain_token(self.key,force_refresh=True).access_token)
                    except Exception as err: raise safe_error(err) from None
                    refreshed=True;continue
                if e.status_code in (429,500,502,503,504) and attempt<4:
                    time.sleep(min(2**attempt,16));continue
                raise safe_error(e) from None
            except Exception as e:
                raise safe_error(e) from None
        raise SafeError('Garmin is temporarily busy. Please refresh again later.')
    def close(self):
        self.client.close();self.auth.close();self.key=None

def safe_error(error):
    status=getattr(error,'status_code',None)
    messages={400:'Garmin rejected this date window or request.',401:'Garmin could not authorise your key. It may have expired or been revoked. Run Setup to replace it.',403:'Garmin denied this request. Check your Personal API key permissions or try again from your home network.',404:'This Garmin dataset is not available for this date or activity.',429:'Garmin’s request limit was reached. Wait a few minutes and refresh again.'}
    return SafeError(messages.get(status,'Garmin could not complete the request. Check your internet connection and try refreshing again.'),status)
