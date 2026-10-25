"""Cross-navigation and selection bounds against synthetic fixture only."""
from playwright.sync_api import sync_playwright
import json
checks=[];errors=[]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=b.new_page(viewport={'width':1440,'height':1000})
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8766');page.wait_for_selector('.fixture-banner')
    def go(name):
        page.locator('nav').get_by_role('button',name=name,exact=name!='Runs').click();page.wait_for_timeout(150)
    def detail():
        page.get_by_label('Classification override').wait_for();checks.append('Source run opened')
    go('Run Comparison');picker=page.locator('.comparison-picker input')
    for i in range(5):picker.nth(i).check()
    assert picker.nth(5).is_disabled();assert page.locator('.comparison-legend button').count()==5
    checks.append('2–5 run comparison cap')
    page.locator('.comparison-legend button').first.click();detail()
    go('Run Comparison');page.get_by_role('button',name='Clear selection',exact=True).click()
    go('Overview');page.get_by_role('button',name='Explore run',exact=True).click();detail()
    page.locator('.similar-list .text-button').filter(has_text='Add pair').first.wait_for()
    page.locator('.similar-list .text-button').filter(has_text='Add pair').first.click()
    page.get_by_role('button',name='Open comparison',exact=False).click();assert page.locator('.comparison-legend button').count()==2
    checks.append('Similar pair selection and comparison navigation')
    go('5K Performance');dot=page.locator('.analysis-chart .recharts-line-dot').first
    dot.scroll_into_view_if_needed();box=dot.bounding_box();page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.wait_for_timeout(150);page.mouse.click(box['x']+box['width']/2,box['y']+box['height']/2);detail()
    checks.append('5K chart point opens run')
    go('Personal Records');page.locator('.record-tile').filter(has=page.get_by_text('5 km',exact=True)).click();detail()
    checks.append('Record opens run')
    go('Calendar');page.locator('.calendar-run').first.click();detail();checks.append('Calendar opens run')
    go('Aerobic Efficiency');page.get_by_label('HR band',exact=True).select_option('150');page.locator('.evidence-list button').first.click();detail()
    checks.append('Band analysis source link')
    go('Observations')
    if page.locator('.insight-row').count():page.locator('.insight-row').first.click();checks.append('Observation opens supporting analysis')
    go('Runs');page.get_by_label('Run classification',exact=True).select_option('Aerobic');go('Fitness Trends')
    assert page.get_by_label('Run classification',exact=True).input_value()=='Aerobic';checks.append('Global filter persists across pages')
    assert not errors,errors
    b.close()
print(json.dumps({'checks':checks,'runtimeErrors':errors},indent=2))
