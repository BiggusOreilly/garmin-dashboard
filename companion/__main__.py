import argparse
import getpass
import os
import sys
import webbrowser
from pathlib import Path
from .store import Store
from .garmin import KEY_FILE,SafeError

def setup():
    if not sys.stdin.isatty():raise SafeError('Please open Setup by double-clicking it in Finder so your key can be entered invisibly.')
    if sys.platform!='darwin':print('This setup is designed for your Mac.')
    KEY_FILE.parent.mkdir(parents=True,exist_ok=True,mode=0o700);KEY_FILE.parent.chmod(0o700)
    if KEY_FILE.is_symlink():raise SafeError('The key file is a symbolic link. Remove that link before setup.')
    if KEY_FILE.exists():
        KEY_FILE.chmod(0o600)
        if input('A local Garmin key already exists. Replace it? [y/N] ').strip().lower()!='y':return
    print('Paste your Garmin Personal API key below. It will stay invisible while you paste; press Return afterward.')
    key=getpass.getpass('Garmin Personal API key (hidden): ').strip()
    if not key:raise SafeError('No key was entered. Run Setup again when you have your key.')
    fd=os.open(KEY_FILE,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:f.write(key+'\n')
    KEY_FILE.chmod(0o600)
    print('Your key is saved privately on this Mac. Double-click Refresh Garmin Data.command next.')

def main():
    os.umask(0o077)
    p=argparse.ArgumentParser(description='Private local Garmin dashboard')
    p.add_argument('action',choices=['setup','refresh','full-refresh','serve','open'])
    p.add_argument('--data-dir',type=Path)
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--history-start',help='Optional earliest health date, YYYY-MM-DD; initial default is earliest activity or one year.')
    args=p.parse_args()
    try:
        if args.action=='setup':setup()
        elif args.action in ('refresh','full-refresh'):
            from .ingest import refresh
            from datetime import date
            store=Store(args.data_dir)
            try:
                if store.meta('synthetic'):raise SafeError('Synthetic fixture databases cannot refresh from Garmin.')
                print('Connecting to Garmin securely. The first import may take a while; keep this window open.',flush=True)
                history=date.fromisoformat(args.history_start) if args.history_start else None
                if args.action=='full-refresh':
                    value=input('Earliest health date to request (YYYY-MM-DD), or Return for earliest activity: ').strip()
                    if value:
                        try: history=date.fromisoformat(value)
                        except ValueError:raise SafeError('That date was not recognised. Please use YYYY-MM-DD, for example 2020-01-01.') from None
                        if history>date.today():raise SafeError('The earliest date cannot be in the future.')
                    store.db.execute("DELETE FROM metadata WHERE key LIKE 'cursor:%' OR key='activities_through'")
                    store.db.commit()
                result=refresh(store,history_start=history,progress=lambda message:print(message,flush=True))
                print(f"Refresh complete. {result['activities']} activities cached on this Mac. {result['warnings']} dataset warnings.")
                print('Open Data / Settings in the dashboard to review availability and any partial imports.')
            finally:store.close()
        else:
            from .server import serve
            if args.action=='open':
                import urllib.request,json
                url=f'http://127.0.0.1:{args.port}'
                try:
                    with urllib.request.urlopen(url+'/api/ping',timeout=2) as r:existing=json.load(r)
                    if existing.get('application')!='stride-local':raise SafeError('Another application is using the dashboard port. Close it and try again.')
                    webbrowser.open(url);return
                except OSError:pass
                from threading import Timer
                Timer(1,lambda:webbrowser.open(url)).start()
            serve(args.data_dir,args.port)
    except SafeError as e:print('\n'+str(e));return 1
    except KeyboardInterrupt:print('\nStopped. Your cached data is safe.');return 0
    except Exception:print('\nThe operation could not finish. Check the setup and try again. No secrets have been displayed.');return 1
    return 0

if __name__=='__main__':sys.exit(main())
