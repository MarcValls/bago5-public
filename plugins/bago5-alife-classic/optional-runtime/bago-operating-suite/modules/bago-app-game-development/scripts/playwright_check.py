#!/usr/bin/env python3
"""Optional Playwright probe: one stable URL, DOM, interaction and screenshot.

Requires external Playwright Python + browser installation (never installs either).
Not a substitute for full E2E test suite, security or accessibility review.
If Pillow is absent, screenshots must match exactly by hash; no silent visual PASS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True)
    p.add_argument('--input-selector',required=True)
    p.add_argument('--container-selector',required=True)
    p.add_argument('--baseline-png',type=Path,required=True)
    p.add_argument('--capture-png',type=Path,required=True)
    p.add_argument('--text',default='bago-test-input')
    p.add_argument('--width',type=int,default=1280)
    p.add_argument('--height',type=int,default=800)
    p.add_argument('--locale',default='es-ES')
    p.add_argument('--dpr',type=float,default=1)
    p.add_argument('--threshold',type=float,default=0,help='max fraction of differing pixels, 0..1')
    a=p.parse_args()
    if not 0<=a.threshold<=1 or a.width<1 or a.height<1 or a.dpr<=0:
        p.error('invalid visual profile')
    if a.capture_png.resolve()==a.baseline_png.resolve() or a.capture_png.exists():
        p.error('refusing to overwrite baseline or existing evidence')
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({'status':'NOT_RUN','error':'Playwright not available'}));return 3
    if not a.baseline_png.is_file():
        print(json.dumps({'status':'NOT_RUN','error':'baseline screenshot missing'}));return 3
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':a.width,'height':a.height},
                         locale=a.locale,device_scale_factor=a.dpr,reduced_motion='reduce')
            page=context.new_page();page.goto(a.url,wait_until='networkidle')
            input_element=page.locator(a.input_selector)
            box=page.locator(a.container_selector)
            assert box.count()==1 and box.is_visible(),'Original container absent'
            assert input_element.count()==1 and input_element.is_visible(),'Input absent'
            a.capture_png.parent.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(a.capture_png),full_page=False,animations='disabled')
            input_element.fill(a.text)
            assert input_element.input_value()==a.text,'Input no longer accepts text'
            browser.close()
        try:
            from PIL import Image, ImageChops
            with Image.open(a.capture_png) as current, Image.open(a.baseline_png) as previous:
                if current.size!=previous.size:raise ValueError('different screenshot size')
                if current.mode!='RGB':current=current.convert('RGB')
                if previous.mode!='RGB':previous=previous.convert('RGB')
                diff=ImageChops.difference(current,previous).convert('L')
                pix=diff.histogram()
                changed=sum(pix[1:]);ratio=changed/(current.width*current.height)
        except ImportError:
            sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
            ratio=0 if sha(a.capture_png)==sha(a.baseline_png) else 1
        good=ratio<=a.threshold
        print(json.dumps({'status':'PASS' if good else 'FAIL','diff_pixel_ratio':ratio,
                          'threshold':a.threshold,'evidence_png':str(a.capture_png),
                          'observed':{'container':True,'editable':True}}))
        return 0 if good else 1
    except Exception as ex:
        print(json.dumps({'status':'ERROR','error':str(ex)}));return 2
if __name__=='__main__':raise SystemExit(main())
