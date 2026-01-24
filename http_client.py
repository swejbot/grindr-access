import pycurl
import json
import zlib
from .utils import gen_l_dev_info


# parser from https://pycurl.io/docs/latest/quickstart.html
class HeaderParser:
        def __init__(self):
            self.headers = {}
    
        def parse_and_append(self, header_line):
            # HTTP standard specifies that headers are encoded in iso-8859-1.
            # On Python 2, decoding step can be skipped.
            # On Python 3, decoding step is required.
            header_line = header_line.decode('iso-8859-1')
    
            # Header lines include the first status line (HTTP/1.x ...).
            # We are going to ignore all lines that don't have a colon in them.
            # This will botch headers that are split on multiple lines...
            if ':' not in header_line:
                return
    
            # Break the header line into header name and value.
            name, value = header_line.split(':', 1)
    
            # Remove whitespace that may be present.
            # Header lines include the trailing newline, and there may be whitespace
            # around the colon.
            name = name.strip()
            value = value.strip()
    
            # Header names are case insensitive.
            # Lowercase name here.
            name = name.lower()
    
            # Now we can actually record the header name and value.
            # Note: this only works when headers are not duplicated, see below.
            self.headers[name] = value
        
        def get(self, name, default=None):
            name = name.lower()
            return self.headers.get(name, default)


class HttpClient:
    base_url = "https://grindr.mobi"
    user_agent = "grindr3/25.20.0.147239;147239;Free;Android 14;sdk_gphone64_x86_64;Google"
    auth_token = None
    proxy = None
    proxy_port = None

    def set_auth_token(self, auth_token):
        self.auth_token = auth_token
    
    def set_proxy(self, proxy, proxy_port):
        self.proxy = proxy
        self.proxy_port = proxy_port

    def get_headers(self):
        return [
            "accept: application/json",
            "accept-encoding: gzip",
            "accept-language: en-US",
            "connection: Keep-Alive",
            "host: grindr.mobi",
            f"l-device-info: {gen_l_dev_info()}",
            "l-locale: en_US",
            "l-time-zone: Europe/Oslo",
            "requirerealdeviceinfo: true",
            f"user-agent: {self.user_agent}",
        ]


    def request_generic(self, method, path, path_params=None, body=None):
        c = pycurl.Curl()

        if self.proxy is not None and self.proxy_port is not None:
            c.setopt(c.PROXY, self.proxy)
            c.setopt(c.PROXYPORT, self.proxy_port)
            c.setopt(c.PROXYTYPE, pycurl.PROXYTYPE_HTTP)
        
        curl_url = self.base_url + path
        if isinstance(path_params, dict):
            curl_url += "?" + "&".join([key + "=" + str(path_params[key]) for key in path_params])

        c.setopt(c.URL, curl_url)
        c.setopt(c.CUSTOMREQUEST, method)

        headers = self.get_headers()

        # if body is list or dict, serialize it to json
        if isinstance(body, (list, dict)):
            data_json = json.dumps(body)
            headers.append("content-type: application/json; charset=UTF-8")
            headers.append("Content-Length: " + str(len(data_json)))
            c.setopt(c.POSTFIELDS, data_json)
        # else, if the body is file-like object, read it as bytes and assume it's an image
        elif hasattr(body, "read"):
            buffer = body.read()
            headers.append("content-type: image/jpeg")
            c.setopt(c.POSTFIELDS, buffer)


        if self.auth_token is not None:
            headers.append("authorization: Grindr3 " + self.auth_token)

        c.setopt(c.HTTPHEADER, headers)

        header_parser = HeaderParser()
        c.setopt(c.HEADERFUNCTION, header_parser.parse_and_append)

        response_data = []
        def handle_response(data):
            response_data.append(data)

        c.setopt(c.WRITEFUNCTION, handle_response)
        c.perform()

        response_data = b"".join(response_data)

        response_obj = self.parse_response(response_data, header_parser)

        if c.getinfo(c.RESPONSE_CODE) / 100 != 2:
            return {
                "error": "HTTP error",
                "status_code": c.getinfo(c.RESPONSE_CODE),
                "response": response_obj
            }
            
        c.close()

        return response_obj



    def parse_response(self, response_data, header_parser):
        if len(response_data) == 0:
            return None
        
        # if the response header content-encoding is gzip, decompress it
        if "gzip" in header_parser.get("content-encoding", ""):
            try:
                response_data = zlib.decompress(response_data, zlib.MAX_WBITS | 16)
            except zlib.error as e:
                return {"error": "Decompression failed", "details": str(e)}

        # if the response is json (Content-Type), parse it
        if "application/json" in header_parser.get("content-type", ""):
            try:
                return json.loads(response_data)
            except json.JSONDecodeError as e:
                return {"error": "JSON decoding failed", "details": str(e)}
        else:
            return {"raw_data": response_data}
    


    def get(self, path, path_params=None, body=None):
        return self.request_generic(
            "GET",
            path,
            path_params,
            body
        )
    
    def post(self, path, path_params=None, body=None):
        return self.request_generic(
            "POST",
            path,
            path_params,
            body
        )

    def put(self, path, path_params=None, body=None):
        return self.request_generic(
            "PUT",
            path,
            path_params,
            body
        )
    
    def delete(self, path, path_params=None, body=None):
        return self.request_generic(
            "DELETE",
            path,
            path_params,
            body
        )
