"""Verify actual rendered chart tooltips; never use live Garmin data."""
from pathlib import Path
import re,json
from playwright.sync_api import sync_playwright
out=Path('/workspace/work/stride-polish-browser-test');checks=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000})
 page.goto('http://127.0.0.1:8766');page.wait_for_selector('.fixture-banner')
 def go(name):page.locator('nav').get_by_role('button',name=name,exact=True).click();page.wait_for_timeout(150)
 go('Data / Settings')
 for theme in ['Green','Blue','Orange','Purple','Red']:
  page.get_by_role('button',name=theme,exact=True).click();page.locator('.appearance').screenshot(path=str(out/f'palette-{theme}.png'))
  go('Training Load')
  card=page.locator('.card').filter(has=page.get_by_role('heading',name='Weekly distance',exact=True));dot=card.locator('.recharts-line-dot').last;dot.scroll_into_view_if_needed();box=dot.bounding_box();page.mouse.move(box['x']+2,box['y']+2);page.wait_for_timeout(150)
  tooltip=page.locator('.stride-tooltip').filter(visible=True) if False else page.locator('.stride-tooltip').first
  text=tooltip.inner_text();assert 'Distance' in text and 'km' in text,text;assert not re.search(r'\d+\.\d{3,}',text),text
  page.screenshot(path=str(out/f'tooltip-{theme}.png'))
  checks.append([theme,text]);go('Data / Settings')
 go('Training Load');card=page.locator('.card').filter(has=page.get_by_role('heading',name='Intensity-weighted minutes',exact=True));dot=card.locator('.recharts-line-dot').last;dot.scroll_into_view_if_needed();box=dot.bounding_box();page.mouse.move(box['x']+2,box['y']+2);page.wait_for_timeout(150);text=page.locator('.stride-tooltip').first.inner_text();assert 'Intensity-weighted minutes' in text and ' min' in text and 'zoneMinutes' not in text,text
 b.close()
print(json.dumps({'formattedTooltips':checks,'intensityTooltip':text},indent=2))
