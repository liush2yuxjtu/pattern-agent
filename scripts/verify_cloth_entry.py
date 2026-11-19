"""Verify the homepage entry reaches the source-bound FreeSewing artifact.

Real Playwright desktop/mobile navigation; a content/link change does not
re-certify calibrated material physics. Browser plugin unavailable.
"""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
EXPECTED=json.loads((ROOT/'docs/verification/cloth-responsive-20261119/candidate.json').read_text())['htmlSHA256']
from verify_pages import local_site
from playwright.sync_api import sync_playwright

def check(base,out):
 out.mkdir(parents=True,exist_ok=True);errors=[];result={'base':base,'checks':{},'errors':errors}
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--enable-unsafe-swiftshader']);page=browser.new_page(viewport={'width':1440,'height':1100});page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
  response=page.goto(base,wait_until='networkidle');result['indexSHA256']=hashlib.sha256(response.body()).hexdigest();assert response.status==200;page.locator('header').screenshot(path=str(out/'desktop-navigation.png'))
  page.get_by_role('link',name='FreeSewing 四片裙',exact=True).click();section=page.locator('#freesewing-lab');assert section.is_visible();text=section.inner_text();result['checks']['scopeAndMetrics']=all(s in text for s in ['466','52/52','193.7%','WebGPU','CPU','固定点','真实合体性未通过验收'])
  evidence=section.get_by_role('link',name='查看原始验证记录 ↗');result['checks']['sourceBoundEvidenceLink']='main/docs/verification/cloth-responsive-20261119' in evidence.get_attribute('href');section.screenshot(path=str(out/'desktop-entry.png'))
  with page.expect_navigation(wait_until='networkidle',timeout=60000) as navigation:section.get_by_role('link',name='打开单文件试衣',exact=False).click()
  response=navigation.value;page.wait_for_function('window.clothLab?.ready',timeout=60000);actual=hashlib.sha256(response.body()).hexdigest();result['checks']['sourceBoundFreeWaistArtifact']=actual==EXPECTED;result['checks']['actualNavigation']=page.title()=='Pattern Agent · FreeSewing Cloth Lab' and page.evaluate('clothLab.stats().steps')==120 and page.evaluate('clothLab.coverageCheck().exposed')==0 and page.evaluate('clothLab.supportStats().fixed')==0 and page.evaluate('clothLab.project().support.gravity_m_s2')==[0,-9.81,0]
  page.get_by_role('button',name='Back',exact=True).click();page.screenshot(path=str(out/'linked-lab-back.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844});page.goto(base,wait_until='networkidle');page.locator('header').screenshot(path=str(out/'mobile-navigation.png'));page.get_by_role('link',name='FreeSewing 四片裙',exact=True).click();section=page.locator('#freesewing-lab');box=section.get_by_role('link',name='打开单文件试衣',exact=False).bounding_box();result['checks']['mobileNoOverflow']=page.evaluate('document.documentElement.scrollWidth<=innerWidth') and box['x']>=0 and box['x']+box['width']<=390;section.screenshot(path=str(out/'mobile-entry.png'));result['checks']['consoleHealthy']=not errors;browser.close()
 result['verdict']='PASS' if all(result['checks'].values()) else 'FAIL';(out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['verdict']=='PASS'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--url');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.url:check(a.url,a.out)
 else:
  with local_site(ROOT/'dist') as base:check(base,a.out)
