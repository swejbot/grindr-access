from .http_client import HttpClient

from .paths import paths
from .utils import to_geohash
import binascii
from functools import wraps


def check_banned(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.banned:
            return
        return func(self, *args, **kwargs)
    return wrapper


class GrindrUser:
    def __init__(self):
        self.banned = False

        self.sessionId = None
        self.profileId = ""
        self.authToken = None
        self.xmppToken = ""

        self.http_client = HttpClient()

    def set_proxy(self, proxy, proxy_port):
        self.http_client.set_proxy(proxy, proxy_port)

    def login(self, email, password):
        response = self.http_client.post(
            paths.SESSIONS,
            body={"email": email, "password": password, "token": ""},
        )

        if "code" in response:
            code = response["code"]

            if code == 30:
                raise Exception("You need to verify your account via phone number!")

            if response["code"] == 27:
                self.banned = True
                raise Exception(f"Banned for {response['reason']}")

            if response["code"] == 28:
                self.banned = True
                raise Exception("Banned")

            if response["code"] == 8:
                raise Exception("Deprecated client version")

        self.sessionId = response["sessionId"]
        self.profileId = response["profileId"]
        self.authToken = response["authToken"]
        self.xmppToken = response["xmppToken"]

        self.http_client.set_auth_token(self.sessionId)

    @check_banned
    def get_profiles(self, lat, lon, searchParams={}, pageNumber=1):
        params = {
            "nearbyGeoHash": to_geohash(lat, lon),
            "onlineOnly": "false",
            "photoOnly": "false",
            "faceOnly": "false",
            "notRecentlyChatted": "false",
            "fresh": "false",
            "pageNumber": str(pageNumber),
            "rightNow": "false",
        }

        params.update(searchParams)

        response = self.http_client.get(
            paths.GET_USERS,
            path_params=params
        )

        return response

    @check_banned
    def get_taps(self):
        response = self.http_client.get(
            paths.TAPS_RECIEVED,
            body={},
        )
        return response

    # type is a number from 1 - ?
    @check_banned
    def tap(self, profileId, type):
        response = self.http_client.post(
            paths.TAP,
            body={"recipientId": profileId, "tapType": type},
        )
        return response

    @check_banned
    def get_profile(self, profileId):
        response = self.http_client.get(
            paths.GET_PROFILE + str(profileId),
        )
        return response

    @check_banned
    def block_profile(self, profileId):
        response = self.http_client.post(
            paths.PROFILE_BLOCKS + str(profileId),
            body={
                "updateTime": 0
            }
        )
        return response

    @check_banned
    def unblock_profile(self, profileId):
        response = self.http_client.delete(
            paths.PROFILE_BLOCKS + str(profileId),
        )
        return response

    @check_banned
    def get_blocked_profiles(self,):
        response = self.http_client.get(
            paths.PROFILE_BLOCK_LIST,
        )
        return response

    # profileIdList MUST be an array of profile ids
    @check_banned
    def get_profile_statuses(self, profileIdList):
        response = self.http_client.post(
            paths.STATUS,
            body={"profileIdList": profileIdList},
        )
        return response

    @check_banned
    def get_album(self, profileId):
        response = self.http_client.post(
            paths.ALBUM,
            body={"profileId": profileId},
        )
        return response

    # returns session data (might renew it)
    @check_banned
    def sessions(self, email):
        response = self.http_client.post(
            paths.SESSIONS,
            body={"email": email, "token": "", "authToken": self.authToken},
        )

        self.sessionId = response["sessionId"]
        self.profileId = response["profileId"]
        self.authToken = response["authToken"]
        self.xmppToken = response["xmppToken"]

        self.http_client.set_auth_token(self.sessionId)

        return response

    @check_banned
    def update_profile(self, data):
        response = self.http_client.put(
            paths.PROFILE,
            body=data,
        )
        return response

    # generating plain auth
    @check_banned
    def generate_plain_auth(self):
        auth = (
            self.profileId
            + "@chat.grindr.com"
            + "\00"
            + self.profileId
            + "\00"
            + self.xmppToken
        )
        _hex = binascii.b2a_base64(str.encode(auth), newline=False)
        _hex = str(_hex)
        _hex = _hex.replace("b'", "").replace("'", "")
        return _hex

    @check_banned
    def upload_image(self, file_io):
        return self.http_client.post(
            "/v3/me/profile/images?thumbCoords=194%2C0%2C174%2C20",
            body=file_io,
        )

    @check_banned
    def set_image(self, primary_hash, secondary_hashes=[]):
        data = {
            "primaryImageHash": primary_hash,
            "secondaryImageHashes": secondary_hashes,
        }

        return self.http_client.put(
            paths.IMAGES, 
            body=data,
        )

    @check_banned
    def set_location(self, lat, lng):
        data = {
            "geohash": to_geohash(lat, lng)
        }

        return self.http_client.put(
            paths.LOCATION,
            body=data,
        )
