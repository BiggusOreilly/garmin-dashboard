"""Production browser checks with synthetic-only fixture, local preferences and no telemetry."""
from pathlib import Path
import json,re
from playwright.sync_api import sync_playwright
out=Path('/workspace/work/stride-polish-browser-test');out.mkdir(parents=True,exist_ok=True)
errors=[];external=[];checks=[]
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
   page.locator('nav').get_by_role('button',name=name,exact=name!='Runs').click();page.wait_for_timeout(180)
  go('Data / Settings');page.get_by_label('Date format',exact=True).select_option('long')
  for theme in ['Green','Blue','Orange','Purple','Red']:
   page.get_by_role('button',name=theme,exact=True).click()
   assert page.locator('html').get_attribute('data-theme')==theme.lower()
   page.screenshot(path=str(out/f'{width}-theme-{theme}.png'),full_page=True)
  page.reload();page.wait_for_selector('.fixture-banner');go('Data / Settings')
  assert page.get_by_label('Date format',exact=True).input_value()=='long'
  assert page.locator('html').get_attribute('data-theme')=='red'
  go('Run Comparison');page.get_by_role('button',name='Clear selection').click()
  for name in ['Turnaround 10K','Garmin 10K','Near 10K effort','Earlier same-day run']:
   page.locator('.comparison-picker label').filter(has_text=name).locator('input').check()
  page.wait_for_timeout(450)
  legend=page.locator('.comparison-legend').inner_text()
  assert legend.index('12 October')<legend.index('22 October')<legend.index('07:00')<legend.index('09:00'),legend
  assert not re.search(r'\b\d{8,}\b',legend)
  assert 'Series0' not in page.locator('main').inner_text()
  page.screenshot(path=str(out/f'{width}-comparison.png'),full_page=True)
  for section in ['Overview','Runs','Running Trends','Fitness Trends','Recovery','Calendar','Personal Records','5K Performance','Observations']:
   go(section)
   if section=='Personal Records':
    page.get_by_label('Record distance',exact=True).select_option('10 km')
    assert page.get_by_text('10 km performance history',exact=True).count()==1
    history=page.locator('.record-history').inner_text()
    assert 'Recorded effort' in history and 'Garmin reported' in history and 'Performance' in history,history
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(width,section)
   content=page.locator('main').inner_text()
   assert not re.search(r'\b\d+\.\d{6,}\b',content),(section,'raw decimals')
   assert '—%' not in content,(section,'missing percent unit')
   assert 'credible' not in content.lower(),section
   assert not re.search(r'\b249711599\d+\b',content),(section,'Garmin ID')
   page.screenshot(path=str(out/f'{width}-{section.replace(" ","-")}.png'),full_page=True)
  go('Runs');page.get_by_label('Search runs',exact=True).fill('Turnaround 10K');page.locator('.run-name').first.click();page.wait_for_selector('.observations')
  assert page.get_by_role('button',name='Revalidate activity data').is_disabled()
  assert page.get_by_role('button',name='HR-band averages',exact=True).count()==1
  page.screenshot(path=str(out/f'{width}-detail.png'),full_page=True)
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
  checks.append({'width':width,'themes':5,'datePreference':'persists','comparison':'chronological with same-day time','10K':'all efforts visible','formatting':'no raw decimals or identifiers'})
  page.close()
 b.close()
assert not errors,errors
assert not external,external
print(json.dumps({'checks':checks,'runtimeErrors':errors,'externalRequests':external},indent=2))
