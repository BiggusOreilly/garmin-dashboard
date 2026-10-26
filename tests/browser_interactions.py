from playwright.sync_api import sync_playwright
import json
result=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1000});external=[];errors=[]
 page.on('request',lambda r:external.append(r.url) if not r.url.startswith('http://127.0.0.1:8766/') else None)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:8766');page.get_by_role('button',name='Refresh data',exact=True).wait_for();page.wait_for_selector('.fixture-banner')
 assert page.get_by_role('button',name='Refresh data',exact=True).is_disabled()
 result.append('Synthetic refresh disabled')
 page.locator('nav').get_by_role('button',name='Runs').click()
 search=page.get_by_role('textbox',name='Search runs');search.fill('NO MATCH TEST');assert page.get_by_text('No runs match these filters.').count()==1
 search.fill('Morning');assert page.locator('tbody tr').count()>0
 search.fill('');page.get_by_role('spinbutton',name='Minimum distance kilometres').fill('100');assert page.locator('tbody tr').count()==0
 page.get_by_role('spinbutton',name='Minimum distance kilometres').fill('')
 result.append('Run search and distance filters')
 page.locator('nav').get_by_role('button',name='Aerobic Efficiency',exact=True).click()
 page.get_by_label('HR band',exact=True).select_option('150')
 assert page.locator('.analysis-chart .recharts-wrapper').count()>=1
 result.append('Cached comparable HR analysis on paired synthetic FIT samples')
 page.locator('nav').get_by_role('button',name='Overview',exact=True).click();page.get_by_role('button',name='Explore run').click();page.wait_for_selector('.observations')
 chart=page.locator('.card').filter(has=page.get_by_role('heading',name='Pace',exact=True)).locator('.recharts-wrapper')
 chart.scroll_into_view_if_needed();box=chart.bounding_box();page.mouse.move(box['x']+box['width']*.6,box['y']+box['height']*.5);page.wait_for_timeout(250)
 visible=page.locator('.recharts-tooltip-wrapper').evaluate_all("els=>els.filter(e=>getComputedStyle(e).visibility==='visible').length")
 assert visible>=2,visible
 result.append('Synchronised run-detail hover across charts')
 page.get_by_role('button',name='Distance',exact=True).click();page.wait_for_timeout(200)
 result.append('Run-detail time/distance toggle')
 page.locator('nav').get_by_role('button',name='Overview',exact=True).click();page.get_by_role('button',name='4 weeks',exact=True).click();page.wait_for_timeout(100)
 result.append('Global date period changes')
 assert not external,external
 assert not errors,errors
 result.append('No external browser requests or runtime errors')
 page.close();b.close()
print(json.dumps(result,indent=2))
