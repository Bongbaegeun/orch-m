#-*- coding: utf-8 -*-
import json
from tornado import httpclient
from tornado.httputil import HTTPHeaders
from tornado.httpclient import HTTPRequest


def sendReq( header, url, _method, _body, timeout=5 ):
    """
    - FUNC: RestAPI로 URL 호출
    - INPUT
        header(M): HTTP Request Header
        url(M): HTTP Request URL
        _method(M): POST
        _body(M): json 형태
        timeout(O): URL 호출 후 timeout 시간
    - OUTPUT : 요청 결과 또는 HTTP Error Response
    """
    http_client = httpclient.HTTPClient()
    h = HTTPHeaders(header)
    strBody = json.dumps( _body )
    _request = HTTPRequest( url, headers=h, method=_method.upper(), validate_cert=False,
                client_cert="/var/onebox/key/client_orch.crt",
                client_key="/var/onebox/key/client_orch.key",
                body=strBody, request_timeout=timeout )
    try:
        response = http_client.fetch( request=_request )
        return response
    except httpclient.HTTPError, e:
        return e.response
    finally:
        http_client.close()





