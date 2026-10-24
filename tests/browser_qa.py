from playwright.sync_api import sync_playwright
import json
from pathlib import Path
out=Path(__file__).resolve().parent.parent/'cache/browser-qa';out.mkdir(parents=True,exist_ok=True)
errors=[];checks=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 for kind,port in [('empty',8765),('synthetic',8766)]:
  for width in [1440,390]:
   page=browser.new_page(viewport={'width':width,'height':1000},device_scale_factor=1)
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
   page.goto(f'http://127.0.0.1:{port}');page.wait_for_selector('h1');page.wait_for_timeout(500)
   page.screenshot(path=str(out/f'{kind}-{width}-overview.png'),full_page=True)
   for section in ['Runs','Running Trends','Recovery','Data / Settings','Overview']:
    if width<620:page.get_by_role('button',name='Open navigation').click()
    page.locator('nav').get_by_role('button',name=section,exact=(section!='Runs')).click()
    page.wait_for_timeout(400)
    overflow=page.evaluate('document.documentElement.scrollWidth>window.innerWidth')
    checks.append([kind,width,section,'overflow' if overflow else 'ok'])
    if section in ['Running Trends','Recovery','Data / Settings']:page.screenshot(path=str(out/f'{kind}-{width}-{section.split()[0]}.png'),full_page=True)
   if kind=='synthetic':
    page.get_by_role('button',name='Explore run').click();page.wait_for_timeout(700)
    page.screenshot(path=str(out/f'{kind}-{width}-detail.png'),full_page=True)
    assert page.get_by_text('Aerobic decoupling',exact=True).count()==1
    page.get_by_role('button',name='Distance',exact=True).click();page.wait_for_timeout(200)
   else:assert page.get_by_text('No Garmin data imported yet.',exact=True).count()==1
   page.close()
 browser.close()
print(json.dumps({'checks':checks,'errors':errors},indent=2))
