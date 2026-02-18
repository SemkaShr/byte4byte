from fastapi import Request
from fastapi.responses import Response
import httpx
from app.challenges.full import FullChallenge
from app.challenges.inject import InjectChallenge

import config
from config import REDIS
import time
import json

from app.endpoint import Endpoint, EndpointResponseStatus
from app.ray.ray import Status as RayStatus
from starlette.requests import ClientDisconnect

class Router:
    def __init__(self, app):
        self.endpoints = {}
        self.logger = config.getLogger('b4b.router')

        @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "UPGRADE"])
        async def proxy(request: Request, path: str):
            try:
                host = request.headers.get('host', 'undefined')
                if host in self.endpoints:
                    endpoint = self.endpoints[host]
                    handle = await endpoint.handleRequest(request)
                    
                    if handle.status in [EndpointResponseStatus.VERFIED, EndpointResponseStatus.JS_CHALLENGE]:
                        if handle.status == EndpointResponseStatus.JS_CHALLENGE:
                            challenge = InjectChallenge(handle.ray)
                            if request.url.path == '/' + challenge.script.getScriptFilename():
                                return Response(challenge.getScriptCode(), media_type='text/javascript')
                            elif request.url.path == challenge.script.getScriptEndpoint():
                                return await challenge.getResponse()
                        
                        response = None
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
                        
                        content = endpointResponse.content
                        contentType = endpointResponse.headers.get('content-type', 'text/html')
                        
                        if handle.status == EndpointResponseStatus.JS_CHALLENGE:
                            injectKey = 'ray:actions:' + handle.ray.group.name + ':' + handle.ray.id + ':inject'
                            noInjectKey = 'ray:actions:' + handle.ray.group.name + ':' + handle.ray.id + ':noInject'
                            
                            if 'text/html' in contentType and content.startswith((b'<!DOCTYPE html>', b'<html')):
                                if not REDIS.exists(injectKey + ':time'):
                                    REDIS.set(injectKey + ':time', time.time(), ex=120)
                                else:
                                    if float(REDIS.get(injectKey + ':time')) - time.time() > 30:
                                        if REDIS.exists(injectKey + ':data'):
                                            if not challenge.predict(json.loads(REDIS.get(injectKey + ':data'))):
                                                print('not verfided by predict: ', handle.ray.ip)
                                        else:
                                            print('where is no data, but time is expired: ', handle.ray.ip)
                                
                                injectCode = challenge.getInjectCode()
                                content += injectCode
                            elif handle.ray.savedScore == None and handle.ray.score == None:
                                if not 'image' in contentType:
                                    if REDIS.exists(noInjectKey):
                                        REDIS.set(noInjectKey, int(config.REDIS.get(noInjectKey)) + 1, ex=60)
                                    else:
                                        REDIS.set(noInjectKey, 1, ex=60)
                                    
                                if REDIS.exists(noInjectKey) and int(config.REDIS.get(noInjectKey)) >= 20:
                                    print('Got limited: ', handle.ray.ip)
                                    handle.ray.status = RayStatus.FULL_JS_CHALLENGE
                                    handle.ray.save()
                                    response = await FullChallenge(handle.ray).getResponse()
                                    REDIS.unlink(noInjectKey)

                        if response == None:
                            response = Response(
                                content,
                                endpointResponse.status_code, 
                                self.getResponseHeaders(endpointResponse.headers)
                            )
        
                            for cookie in [v.decode('utf-8') for k, v in endpointResponse.headers.raw if k.lower() == b'set-cookie']:
                                response.headers.append('set-cookie', cookie)
                                
                            response.headers['content-length'] = str(len(content))
                    elif handle.status == EndpointResponseStatus.FULL_JS_CHALLENGE:
                        response = await FullChallenge(handle.ray).getResponse()
                    elif handle.status == EndpointResponseStatus.BLOCKED:
                        response = Response(config.PAGE_403.replace('{{RAY_ID}}', handle.ray.getShortID()), 403)
                    else:
                        response = Response('Sorry! Status: ' + handle.status.value + '. Ray ID: ' + handle.ray.getShortID())

                    if not config.RAY_NAME in request.cookies or request.cookies[config.RAY_NAME] != handle.ray.id:
                       response.set_cookie(config.RAY_NAME, handle.ray.id, 32140800)

                    return response
                else:
                    return Response('Undefined host', 404)
            except ClientDisconnect as e:
                return Response(config.PAGE_503, 503)
            except Exception as e:
                self.logger.exception(str(type(e)) + ': ' + str(e))
                return Response(config.PAGE_503, 503)
            
        
    def addEndpoint(self, endpoint : Endpoint):
        self.endpoints[endpoint.host] = endpoint

    def getRequestHeaders(self, request):
        result = {k: v for k, v in request.headers.items() if k.lower() not in config.APP_HEADERS}
        result['x-byte4byte-ip'] = request.headers.get('x-forwarded-for')
        result['accept-encoding'] = 'identity'
        return result

    def getResponseHeaders(self, headers):
        result = {k: v for k, v in headers.items() if k.lower() not in ['content-encoding', 'set-cookie', 'server', 'content-length']}
        return result
