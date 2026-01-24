from fastapi import Request
from fastapi.responses import Response
import httpx
import logging
from app.captcha import Captcha

import config

from app.endpoint import Endpoint, EndpointResponseStatus

class Router:
    def __init__(self, app):
        self.endpoints = {}
        self.logger = config.getLogger('b4b.router')

        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "UPGRADE"])
        async def proxy(request: Request, path: str):
            try:
                host = request.headers['host']
                if host in self.endpoints:
                    endpoint = self.endpoints[host]
                    handle = await endpoint.handleRequest(request)
                    
                    if handle.status == EndpointResponseStatus.VERFIED:
                        body = await request.body()

                        try:
                            async with httpx.AsyncClient(follow_redirects=False, verify=False, cookies=request.cookies) as client:
                                endpointResponse = await client.request(
                                    method=request.method,
                                    url=endpoint.getAddress() + path,
                                    content=body,
                                    headers=self.getRequestHeaders(request),
                                    params=request.query_params,
                                    timeout=120
                                )
                        except Exception as e:
                            return Response(config.PAGE_502.replace('{{RAY_ID}}', handle.ray.getShortID()).replace('{{ENDPOINT_HOST}}', endpoint.host), 502)

                        response = Response(
                            endpointResponse.content,
                            endpointResponse.status_code, 
                            self.getResponseHeaders(endpointResponse.headers)
                        )
    
                        for cookie in [v.decode('utf-8') for k, v in endpointResponse.headers.raw if k.lower() == b'set-cookie']:
                            response.headers.append('set-cookie', cookie)
                    elif handle.status == EndpointResponseStatus.CAPTCHA:
                        response = Captcha(handle.ray).getResponse()
                    else:
                        response = Response('Sorry! Status: ' + handle.status.value + '. Ray ID: ' + handle.ray.getShortID())

                    if not config.RAY_NAME in request.cookies or request.cookies[config.RAY_NAME] != handle.ray.id:
                       response.set_cookie(config.RAY_NAME, handle.ray.id, config.RAY_LIFETIME * 2)

                    return response
                else:
                    return Response('Undefined host', 404)
            except Exception as e:
                self.logger.exception(str(type(e)) + ': ' + str(e))
                return Response(config.PAGE_503, 503)
            
        
    def addEndpoint(self, endpoint : Endpoint):
        self.endpoints[endpoint.host] = endpoint

    def getRequestHeaders(self, request):
        result = {k: v for k, v in request.headers.items()}
        result['x-byte4byte-ip'] = request.client.host
        result['accept-encoding'] = 'identity'
        return result

    def getResponseHeaders(self, headers):
        result = {k: v for k, v in headers.items() if k.lower() not in ['content-encoding', 'set-cookie', 'server']}
        return result
