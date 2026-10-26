"""Evidence-tier UI regression, using only tests/seed_five_k.py data."""
from pathlib import Path
import json
import re
from playwright.sync_api import sync_playwright
out=Path('/workspace/work/stride-fivek-browser-test');out.mkdir(parents=True,exist_ok=True)
checks=[];errors=[];external=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    for width in [1440,390]:
        page=b.new_page(viewport={'width':width,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        page.on('request',lambda r:external.append(r.url) if not r.url.startswith('http://127.0.0.1:8767/') else None)
        page.goto('http://127.0.0.1:8767');page.wait_for_selector('.fixture-banner')
        def go(name):
            if width<620:page.get_by_role('button',name='Open navigation').click()
            page.locator('nav').get_by_role('button',name=name,exact=True).click();page.wait_for_timeout(200)
        payload=page.request.get('http://127.0.0.1:8767/api/dashboard').json()
        assert [x['seconds'] for x in payload['records']['5 km']]==[1792,1770,1609]
        assert payload['records']['5 km'][-1]['evidence']=='Garmin reported'
        go('5K Performance')
        assert '26:49 · Garmin reported' in page.locator('.featured').inner_text()
        assert page.locator('.five-k-table tbody tr').count()==7
        assert page.locator('.five-k-table .evidence-badge.reported').count()==2
        assert page.locator('.five-k-table .evidence-badge.sensor').count()==2
        assert page.locator('.five-k-table .evidence-badge.flagged').count()==3
        assert page.get_by_role('heading',name='Garmin-reported and summary-only 5K results').count()==0
        row=page.locator('.five-k-table tbody tr').filter(has_text='Garmin summary PB')
        assert row.locator('td').nth(3).inner_text()=='— / —'
        assert row.locator('td').nth(5).inner_text()=='—'
        row.locator('summary').click();assert 'Invalid intervals' in row.inner_text()
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        page.screenshot(path=str(out/f'{width}-5K.png'),full_page=True)
        row.get_by_role('button').click();page.get_by_label('Classification override').wait_for()
        assert page.get_by_role('button',name='Revalidate activity data',exact=True).is_disabled()
        assert 'Garmin reported' in page.locator('.validation-note').first.inner_text()
        page.screenshot(path=str(out/f'{width}-detail.png'),full_page=True)
        go('Personal Records');tile=page.get_by_role('button',name=re.compile(r'^5 km '))
        assert '26:49' in tile.inner_text();assert 'Garmin reported' in tile.inner_text()
        page.screenshot(path=str(out/f'{width}-records.png'),full_page=True)
        go('Fitness Trends');card=page.locator('.card').filter(has=page.get_by_role('heading',name='Best credible 5K performance',exact=True))
        assert card.locator('.recharts-line-dot').count()>0
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
        go('Running Trends');kpi=page.locator('.kpi').filter(has_text='Credible 5K best');assert '26:49' in kpi.inner_text();assert 'Garmin reported' in kpi.inner_text()
        checks.append({'width':width,'PB':'26:49 Garmin reported','uniqueRows':7,'tiers':'A/B/C visible','navigation':'passed'})
        page.close()
    b.close()
assert not errors,errors
assert not external,external
print(json.dumps({'checks':checks,'runtimeErrors':errors,'externalRequests':external},indent=2))
