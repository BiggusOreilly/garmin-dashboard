"""Loopback-only server with Host/Origin validation, no telemetry or remote assets."""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from threading import Thread, Lock
from .store import Store
from .analysis import dashboard,detail_metrics
from .ingest import refresh
from .garmin import SafeError

STATIC=Path(__file__).parent/'static'

def serve(directory=None,port=8765):
    state={'running':False,'message':None};guard=Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def safe(self,write=False):
            allowed={f'127.0.0.1:{port}',f'localhost:{port}'}
            if self.headers.get('Host') not in allowed:return False
            origin=self.headers.get('Origin')
            if origin and origin not in {f'http://{h}' for h in allowed}:return False
            if self.headers.get('Sec-Fetch-Site')=='cross-site':return False
            if write and self.headers.get('X-Stride-Local')!='1':return False
            return True
        def send(self,code,body,ctype='application/json'):
            self.send_response(code)
            for k,v in {'Content-Type':ctype,'Content-Length':str(len(body)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"}.items():self.send_header(k,v)
            self.end_headers();self.wfile.write(body)
        def js(self,value,code=200):self.send(code,json.dumps(value,allow_nan=False).encode())
        def do_GET(self):
            if not self.safe():return self.js({'error':'Local access only.'},403)
            path=urlparse(self.path).path
            if path=='/api/ping':return self.js({'application':'stride-local','version':1})
            if path=='/api/sync':return self.js(state)
            if path.startswith('/api/'):
                store=Store(directory)
                try:
                    if path=='/api/dashboard':return self.js(dashboard(store))
                    if path.startswith('/api/run/'):
                        aid=path.rsplit('/',1)[-1]
                        if not aid.isdecimal() or store.get('activities',aid) is None:return self.js({'error':'Run not found.'},404)
                        series=store.get('series',aid) or {'records':[],'laps':[]}
                        # Only the coordinate-free, explicitly projected series is returned.
                        return self.js({'series':series,'analysis':detail_metrics(series)})
                    return self.js({'error':'Not found.'},404)
                except Exception:return self.js({'error':'Local data could not be read. Please restart the dashboard.'},500)
                finally:store.close()
            relative=path.lstrip('/') or 'index.html'
            file=(STATIC/relative).resolve()
            if not file.is_relative_to(STATIC.resolve()):return self.js({'error':'Not found.'},404)
            if not file.is_file():file=STATIC/'index.html'
            if not file.is_file():return self.js({'error':'Compiled dashboard assets are missing. Re-download the complete application.'},503)
            self.send(200,file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        def do_POST(self):
            if not self.safe(True):return self.js({'error':'Local access only.'},403)
            if self.path!='/api/refresh':return self.js({'error':'Not found.'},404)
            if not guard.acquire(blocking=False):return self.js({'error':'Refresh already running.'},409)
            state.update(running=True,message='Fetching your Garmin data locally…')
            def job():
                store=Store(directory)
                try:
                    if store.meta('synthetic'):raise SafeError('Test fixtures cannot connect to Garmin. Open the production dashboard to refresh.')
                    result=refresh(store,progress=lambda message:state.update(message=message))
                    state['message']=f"Refresh complete: {result['activities']} activities. {result['warnings']} dataset warnings."
                except SafeError as e:state['message']=str(e)
                except Exception:state['message']='Refresh stopped safely. Please try the Refresh Garmin Data launcher.'
                finally:store.close();state['running']=False;guard.release()
            Thread(target=job,daemon=True).start();self.js({'started':True},202)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(f'Stride dashboard ready at http://127.0.0.1:{port}',flush=True)
    server.serve_forever()
