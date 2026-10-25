"""Local browser QA against explicitly synthetic data, screenshots outside source."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('/workspace/work/stride-expanded-browser-test');out.mkdir(parents=True,exist_ok=True)
errors=[];checks=[];external=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width in [1440,390]:
        page=b.new_page(viewport={'width':width,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('request',lambda r:external.append(r.url) if not r.url.startswith('http://127.0.0.1:8766/') else None)
        page.goto('http://127.0.0.1:8766');page.wait_for_selector('.fixture-banner')
        def go(name):
            if width<620:page.get_by_role('button',name='Open navigation').click()
            page.locator('nav').get_by_role('button',name=name,exact=name!='Runs').click()
            page.wait_for_timeout(350)
        go('Run Comparison')
        picker=page.locator('.comparison-picker input')
        picker.nth(0).check();picker.nth(1).check();page.wait_for_timeout(500)
        assert page.get_by_role('heading',name='Run comparison',exact=True).count()==1
        page.get_by_label('Comparison axis').select_option('distance')
        for section in ['Overview','Runs','Run Comparison','Aerobic Efficiency','HR at Pace','Fitness Trends','5K Performance','Personal Records','Training Load','Recovery','Calendar','Observations','Data / Settings']:
            go(section)
            if section=='Aerobic Efficiency':page.get_by_label('HR band',exact=True).select_option('150');page.wait_for_timeout(100)
            if section=='Recovery':page.get_by_label('Recovery lag').select_option('2')
            if section=='Calendar':page.get_by_label('Calendar view').select_option('week');page.get_by_label('Calendar view').select_option('month')
            page.screenshot(path=str(out/f'{width}-{section.replace(" / ","-").replace(" ","-")}.png'),full_page=True)
            assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth+1'),(width,section,'overflow')
            checks.append([width,section,'layout passed'])
        go('Overview');page.get_by_role('button',name='Explore run',exact=True).click();page.wait_for_selector('.similar-list')
        page.get_by_label('Classification override').select_option('Easy');page.wait_for_timeout(500)
        assert page.get_by_label('Classification override').input_value()=='Easy'
        page.get_by_label('Classification override').select_option('');page.wait_for_timeout(500)
        page.get_by_role('button',name='Distance',exact=True).click()
        page.screenshot(path=str(out/f'{width}-Run-Detail.png'),full_page=True)
        assert not page.evaluate('document.documentElement.scrollWidth>window.innerWidth+1'),(width,'detail','overflow')
        checks.append([width,'Run Detail override and axis','passed'])
        page.close()
    b.close()
assert not errors,errors
assert not external,external
print(json.dumps({'checks':checks,'runtimeErrors':errors,'externalRequests':external},indent=2))
