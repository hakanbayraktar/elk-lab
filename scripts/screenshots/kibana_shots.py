"""elk-lab README'leri icin isaretli Kibana ekran goruntuleri.

Kullanim (yerelde, sunucuya SSH tuneli acikken):
    ssh -N -L 15601:127.0.0.1:15601 student@<sunucu> &
    python3 scripts/screenshots/kibana_shots.py lab01 [lab05 lab06]

Her goruntude tiklanacak yerler kirmizi kutu + ok + adim numarasiyla isaretlenir.
Kutu konumu sabit koordinatla degil, Playwright'in buldugu ogenin olculen yeriyle
cizilir; Kibana arayuzu biraz kaysa da kutu dogru yere duser.
Cikti: assets/screenshots/<lab>/<ad>.png (genislik 1600 px).
"""
import os
import re
import sys
import time

from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

BASE = os.environ.get("KB_BASE", "http://127.0.0.1:15601")
PW = os.environ.get("KB_PASS", "DevOps2026!")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCALE = 1.5          # device_scale_factor
OUT_W = 1600         # kaydedilen genislik
RED = (220, 38, 38)


def login(page):
    page.goto(BASE + "/login", wait_until="domcontentloaded")
    page.fill('input[name="username"]', "elastic")
    page.fill('input[name="password"]', PW)
    page.click('button[type="submit"]')
    page.wait_for_url(lambda u: "/app/" in u or "space_selector" in u, timeout=60000)
    if "space_selector" in page.url:
        page.goto(BASE + "/app/home", wait_until="domcontentloaded")
        time.sleep(3)


def settle(page, extra=3):
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    time.sleep(extra)
    for txt in ("Dismiss", "Got it", "Close tour", "Maybe later"):
        for loc in (page.get_by_role("button", name=txt), page.get_by_text(txt, exact=True)):
            try:
                loc.first.click(timeout=800)
            except Exception:
                pass
    time.sleep(0.5)


def locate(page, target):
    """target: ('text', 'Agents') | ('role', 'tab', 'Agents') | ('css', 'selector') | ('label', 'Period')."""
    kind = target[0]
    if kind == "text":
        loc = page.get_by_text(target[1], exact=target[2] if len(target) > 2 else False)
    elif kind == "role":
        loc = page.get_by_role(target[1], name=target[2], exact=target[3] if len(target) > 3 else False)
    elif kind == "label":
        loc = page.get_by_label(target[1])
    elif kind == "testsubj":
        loc = page.locator(f'[data-test-subj="{target[1]}"]')
    else:
        loc = page.locator(target[1])
    return loc.first


def box_of(page, target):
    if target[0] == "union":   # ('union', t1, t2, ...): hepsini saran tek kutu
        bs = [box_of(page, t) for t in target[1:]]
        x0 = min(b["x"] for b in bs); y0 = min(b["y"] for b in bs)
        x1 = max(b["x"] + b["width"] for b in bs); y1 = max(b["y"] + b["height"] for b in bs)
        return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}
    b = locate(page, target).bounding_box(timeout=10000)
    if not b:
        raise RuntimeError(f"oge bulunamadi: {target}")
    return b


def draw(path, marks):
    """marks: [(bbox, no, arrow_dir)], bbox CSS px; arrow_dir: 'left'|'right'|'up'|'down'|None."""
    im = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    pad = 6 * SCALE
    for b, no, arrow in marks:
        x0, y0 = b["x"] * SCALE - pad, b["y"] * SCALE - pad
        x1, y1 = (b["x"] + b["width"]) * SCALE + pad, (b["y"] + b["height"]) * SCALE + pad
        d.rounded_rectangle((x0, y0, x1, y1), radius=8, outline=RED, width=5)
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        L = 110
        if arrow == "left":      # ok soldan saga, kutunun sol kenarina
            tip, tail = (x0 - 4, cy), (x0 - L, cy)
        elif arrow == "right":
            tip, tail = (x1 + 4, cy), (x1 + L, cy)
        elif arrow == "up":
            tip, tail = (cx, y0 - 4), (cx, y0 - L)
        elif arrow == "down":
            tip, tail = (cx, y1 + 4), (cx, y1 + L)
        else:
            tip = tail = None
        if tip:
            d.line((tail, tip), fill=RED, width=7)
            import math
            ang = math.atan2(tip[1] - tail[1], tip[0] - tail[0])
            h = 26
            p1 = (tip[0] - h * math.cos(ang - 0.45), tip[1] - h * math.sin(ang - 0.45))
            p2 = (tip[0] - h * math.cos(ang + 0.45), tip[1] - h * math.sin(ang + 0.45))
            d.polygon([tip, p1, p2], fill=RED)
            nx, ny = tail
        else:
            nx, ny = x0, y0
        if no is None:
            continue
        r = 24
        d.ellipse((nx - r - 3, ny - r - 3, nx + r + 3, ny + r + 3), fill=(255, 255, 255))
        d.ellipse((nx - r, ny - r, nx + r, ny + r), fill=RED)
        t = str(no)
        tw, th = d.textbbox((0, 0), t, font=font)[2:]
        d.text((nx - tw / 2, ny - th / 2 - 3), t, fill=(255, 255, 255), font=font)
    if im.width > OUT_W:
        im = im.resize((OUT_W, int(im.height * OUT_W / im.width)), Image.LANCZOS)
    im.save(path, optimize=True)


def shoot(page, lab, name, marks_spec, scroll_to=None):
    """Once scroll_to (yoksa ilk isaret) gorunur yapilir, sonra butun kutular ayni anda olculur."""
    out_dir = os.path.join(ROOT, "assets", "screenshots", lab)
    os.makedirs(out_dir, exist_ok=True)
    first = scroll_to or (marks_spec[0][0] if marks_spec else None)
    while first and first[0] == "union":
        first = first[1]
    if first:
        locate(page, first).scroll_into_view_if_needed(timeout=10000)
        time.sleep(1)
    marks = []
    for target, no, arrow in marks_spec:
        marks.append((box_of(page, target), no, arrow))
    path = os.path.join(out_dir, name + ".png")
    page.screenshot(path=path)
    draw(path, marks)
    print("ok", os.path.relpath(path, ROOT))


# ---------------------------------------------------------------- lab akislari
def tid(name):
    return ("testsubj", name)


def kibana_delete_by_title(page, so_type, title):
    """Onceki denemeden kalan nesneyi siler (yalniz goruntu alma hazirligi)."""
    r = page.request.get(BASE + f"/api/saved_objects/_find?type={so_type}&per_page=100",
                         headers={"kbn-xsrf": "x"})
    for o in r.json().get("saved_objects", []):
        if o["attributes"].get("title") == title or o["attributes"].get("name") == title:
            page.request.delete(BASE + f"/api/saved_objects/{so_type}/{o['id']}?force=true",
                                headers={"kbn-xsrf": "x"})


def console_text(page, text):
    page.locator(".monaco-editor").first.click(); time.sleep(0.5)
    page.keyboard.press("Meta+A"); page.keyboard.press("Delete")
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    page.evaluate("t => navigator.clipboard.writeText(t)", text)
    page.keyboard.press("Meta+V"); time.sleep(1)


def lab01(page):
    lab = "LAB-ELK-01"
    page.goto(BASE + "/app/home", wait_until="domcontentloaded"); settle(page, 4)
    try:   # ilk giris: Welcome to Elastic ekrani (README Adim 4)
        page.get_by_role("button", name="Explore on my own").click(timeout=4000); settle(page, 3)
    except Exception:
        pass
    page.locator('[data-test-subj="toggleNavButton"]').click(); time.sleep(2)
    nav = page.locator('[data-test-subj="collapsibleNav"]')
    link = nav.get_by_role("link", name="Dev Tools").first
    link.scroll_into_view_if_needed(); time.sleep(1)
    shoot(page, lab, "01-devtools-menu", [
        (("css", '[data-test-subj="toggleNavButton"]'), 1, "down"),
        (("css", '[data-test-subj="collapsibleNav"] a:has-text("Dev Tools")'), 2, "right"),
    ], scroll_to=("css", '[data-test-subj="collapsibleNav"] a:has-text("Dev Tools")'))
    page.goto(BASE + "/app/dev_tools#/console", wait_until="domcontentloaded"); settle(page, 5)
    for t in ("Skip tour",):
        try:
            page.get_by_role("button", name=t).click(timeout=3000)
        except Exception:
            pass
    console_text(page, 'GET devops-envanter/_search\n{\n  "query": { "match": { "durum": "aktif" } }\n}\n')
    page.locator(".monaco-editor .view-line").first.click(); time.sleep(1)
    page.locator('[data-test-subj="sendRequestButton"]').first.click(); time.sleep(4)
    shoot(page, lab, "02-devtools-run", [
        (("css", ".monaco-editor >> nth=0"), 3, None),
        (("css", '[data-test-subj="sendRequestButton"]'), 4, "down"),
    ])


def paste_into(page, locator, text):
    locator.click(); time.sleep(0.5)
    page.keyboard.press("Meta+A"); page.keyboard.press("Delete")
    page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    page.evaluate("t => navigator.clipboard.writeText(t)", text)
    page.keyboard.press("Meta+V"); time.sleep(1)


def lab03(page):
    lab = "LAB-ELK-03"
    page.goto(BASE + "/app/dev_tools#/grokdebugger", wait_until="domcontentloaded"); settle(page, 5)
    eds = page.locator(".monaco-editor")
    paste_into(page, eds.nth(0), '172.31.0.1 - - [19/Nov/2026:16:05:12 +0000] "GET /urunler HTTP/1.1" 404 153 "-" "Mozilla/5.0" "-"')
    paste_into(page, eds.nth(1), "%{COMBINEDAPACHELOG}")
    page.locator('[data-test-subj="btnSimulate"]').click(); time.sleep(4)
    page.set_viewport_size({"width": 1600, "height": 1060}); time.sleep(1)
    shoot(page, lab, "01-grok-debugger", [
        (("css", ".monaco-editor >> nth=0"), 1, None),
        (("css", ".monaco-editor >> nth=1"), 2, None),
        (tid("btnSimulate"), 3, "right"),
        (("css", 'xpath=//*[normalize-space(text())="Structured Data"]/following::pre[1]'), 4, None),
    ], scroll_to=tid("btnSimulate"))
    page.set_viewport_size({"width": 1600, "height": 900})


def lab05(page):
    lab = "LAB-ELK-05"
    # Adim 1: hazir panolar listesi
    page.goto(BASE + "/app/dashboards#/list", wait_until="domcontentloaded"); settle(page, 5)
    shoot(page, lab, "01-dashboard-list", [
        (("union", ("role", "link", "Uygulama Trafiği ve Hatalar"), ("role", "link", "Güvenlik: SSH ve Firewall"),
          ("role", "link", "Kubernetes ve CI/CD"), ("role", "link", "SSH ve Hatalar (betik)")), 1, "right"),
    ])
    # Adim 2: data view olustur (onceki denemeden kalani sil)
    kibana_delete_by_title(page, "index-pattern", "Sistem Logları")
    kibana_delete_by_title(page, "dashboard", "SSH ve Hatalar")
    page.goto(BASE + "/app/management/kibana/dataViews", wait_until="domcontentloaded"); settle(page, 4)
    shoot(page, lab, "02-create-data-view", [((tid("createDataViewButton")), 2, "down")])
    page.locator('[data-test-subj="createDataViewButton"]').first.click(); time.sleep(2)
    page.locator('[data-test-subj="createIndexPatternNameInput"]').fill("Sistem Logları")
    page.locator('[data-test-subj="createIndexPatternTitleInput"]').fill("system-logs-*"); time.sleep(3)
    shoot(page, lab, "03-data-view-form", [
        (tid("createIndexPatternNameInput"), 3, "left"),
        (tid("createIndexPatternTitleInput"), 4, "left"),
        (tid("saveIndexPatternButton"), 5, "up"),
    ])
    page.locator('[data-test-subj="saveIndexPatternButton"]').click(); settle(page, 4)
    # Adim 3: Discover
    page.goto(BASE + "/app/discover#/?_g=(time:(from:now-24h,to:now))", wait_until="domcontentloaded"); settle(page, 6)
    page.locator('[data-test-subj="discover-dataView-switch-link"]').click(); time.sleep(1.5)
    page.locator('[data-test-subj="indexPattern-switcher--input"]').fill("Sistem"); time.sleep(1.5)
    page.get_by_role("option").filter(has_text=re.compile(r"^Sistem Logları")).first.click(); settle(page, 5)
    q = page.locator('[data-test-subj="queryInput"]')
    q.click(); q.fill('event.outcome : "failure"'); page.keyboard.press("Enter"); settle(page, 6)
    shoot(page, lab, "04-discover-kql", [
        (tid("discover-dataView-switch-link"), 6, "down"),
        (tid("queryInput"), 7, "down"),
    ])
    # Adim 4: Lens ile panel ve pano
    page.goto(BASE + "/app/dashboards#/create", wait_until="domcontentloaded"); settle(page, 5)
    shoot(page, lab, "05-create-visualization", [(("role", "button", "Create visualization"), 8, "down")])
    page.get_by_role("button", name="Create visualization").first.click(); settle(page, 6)
    page.locator('[data-test-subj="lns-dataView-switch-link"]').click(); time.sleep(1.5)
    page.locator('[data-test-subj="indexPattern-switcher--input"]').fill("Sistem"); time.sleep(1.5)
    page.get_by_role("option").filter(has_text=re.compile(r"^Sistem Logları")).first.click(); settle(page, 4)
    q = page.locator('[data-test-subj="queryInput"]')
    q.click(); q.fill('event.outcome : "failure"'); page.keyboard.press("Enter"); time.sleep(2)
    page.locator('[data-test-subj="lnsIndexPatternFieldSearch"]').fill("source.ip"); time.sleep(1.5)
    field = page.locator('[data-test-subj="lnsFieldListPanelField-source.ip.keyword"]')
    field.drag_to(page.locator('[data-test-subj="lnsWorkspace"]')); settle(page, 6)
    shoot(page, lab, "06-lens-drag-field", [
        (tid("lns-dataView-switch-link"), 9, "down"),
        (tid("queryInput"), 10, "down"),
        (tid("lnsFieldListPanelField-source.ip.keyword"), 11, "right"),
        (tid("lnsApp_saveAndReturnButton"), 12, "down"),
    ])
    page.locator('[data-test-subj="lnsApp_saveAndReturnButton"]').click(); settle(page, 6)
    # ikinci panel: hazir panodaki "En cok 5xx veren servisler"
    page.get_by_role("button", name="Create visualization").first.click(); settle(page, 6)
    page.locator('[data-test-subj="lns-dataView-switch-link"]').click(); time.sleep(1.5)
    page.locator('[data-test-subj="indexPattern-switcher--input"]').fill("Demo Uygulama"); time.sleep(1.5)
    page.get_by_role("option").filter(has_text="Demo Uygulama Logları").first.click(); settle(page, 4)
    page.locator('[data-test-subj="superDatePickerToggleQuickMenuButton"]').click(); time.sleep(1)
    page.get_by_text("Last 24 hours", exact=True).first.click(); time.sleep(2)
    q = page.locator('[data-test-subj="queryInput"]')
    q.click(); q.fill("http.response.status_code >= 500"); page.keyboard.press("Enter"); time.sleep(2)
    page.locator('[data-test-subj="lnsIndexPatternFieldSearch"]').fill("service.name"); time.sleep(1.5)
    page.locator('[data-test-subj="lnsFieldListPanelField-service.name"]').drag_to(
        page.locator('[data-test-subj="lnsWorkspace"]')); settle(page, 5)
    shoot(page, lab, "07-lens-5xx-panel", [
        (tid("lns-dataView-switch-link"), 13, "down"),
        (tid("superDatePickerToggleQuickMenuButton"), 14, "down"),
        (tid("queryInput"), 15, "down"),
        (tid("lnsFieldListPanelField-service.name"), 16, "right"),
        (tid("lnsApp_saveAndReturnButton"), 17, "down"),
    ])
    page.locator('[data-test-subj="lnsApp_saveAndReturnButton"]').click(); settle(page, 6)
    page.locator('[data-test-subj="dashboardInteractiveSaveMenuItem"]').click(); time.sleep(2)
    page.locator('[data-test-subj="savedObjectTitle"]').fill("SSH ve Hatalar"); time.sleep(1)
    shoot(page, lab, "08-save-dashboard", [
        (tid("savedObjectTitle"), 18, "left"),
        (tid("confirmSaveSavedObjectButton"), 19, "up"),
    ])
    page.locator('[data-test-subj="confirmSaveSavedObjectButton"]').click(); settle(page, 6)
    page.screenshot(path=os.path.join(ROOT, "..", "check", "lab05-final.png"))


def combo_add(page, root, text):
    box = page.locator(f'[data-test-subj="{root}"]')
    box.locator('[data-test-subj="comboBoxSearchInput"]').click(); time.sleep(0.5)
    page.keyboard.type(text); time.sleep(1.5); page.keyboard.press("Enter"); time.sleep(1)


def lab06_create_rule(page):
    """README Adim 1: SSH threshold kuralini arayuzden kurma."""
    lab = "LAB-ELK-06"
    page.set_viewport_size({"width": 1600, "height": 1100})
    page.request.post(BASE + "/api/detection_engine/rules/_bulk_action", headers={"kbn-xsrf": "x"},
                      data={"action": "delete", "query": 'alert.attributes.name:"SSH brute force*"'})
    page.goto(BASE + "/app/security/rules/create", wait_until="domcontentloaded"); settle(page, 8)
    page.locator('[data-test-subj="thresholdRuleType"]').click(); time.sleep(2)
    shoot(page, lab, "01-rule-type", [(tid("thresholdRuleType"), 1, "down")])
    idx = page.locator('[data-test-subj="detectionEngineStepDefineRuleIndices"]')
    idx.locator('[data-test-subj="comboBoxClearButton"]').click(); time.sleep(1)
    combo_add(page, "detectionEngineStepDefineRuleIndices", "system-logs-*")
    q = page.locator('[data-test-subj="detectionEngineStepDefineRuleQueryBar"] [data-test-subj="queryInput"]')
    q.click(); q.fill('event.category : "authentication" and event.outcome : "failure"'); time.sleep(1)
    combo_add(page, "detectionEngineStepDefineRuleThresholdField", "source.ip.keyword")
    v = page.locator('[data-test-subj="detectionEngineStepDefineRuleThresholdValue"] input')
    v.fill("5"); time.sleep(1)
    shoot(page, lab, "02-define-rule", [
        (tid("detectionEngineStepDefineRuleIndices"), 2, "left"),
        (tid("detectionEngineStepDefineRuleQueryBar"), 3, "left"),
        (tid("detectionEngineStepDefineRuleThresholdField"), 4, "left"),
        (tid("detectionEngineStepDefineRuleThresholdValue"), 5, "right"),
    ], scroll_to=tid("detectionEngineStepDefineRuleQueryBar"))
    page.locator('[data-test-subj="define-continue"]').click(); settle(page, 4)
    page.locator('[data-test-subj="detectionEngineStepAboutRuleName"] input').fill("SSH brute force: aynı IP'den 5+ başarısız giriş")
    page.locator('[data-test-subj="detectionEngineStepAboutRuleDescription"] textarea').fill("Son 6 dakikada aynı kaynak IP'den en az 5 başarısız SSH girişi.")
    page.locator('[data-test-subj="detectionEngineStepAboutRuleSeverity"] [data-test-subj="select"]').click(); time.sleep(1)
    page.get_by_role("option", name="High").first.click(); time.sleep(1)
    combo_add(page, "detectionEngineStepAboutRuleTags", "elk-lab")
    page.locator('[data-test-subj="detectionEngineStepAboutRuleName"]').scroll_into_view_if_needed()
    page.mouse.wheel(0, -160); time.sleep(1)
    shoot(page, lab, "03-about-rule", [
        (tid("detectionEngineStepAboutRuleName"), 6, "left"),
        (tid("detectionEngineStepAboutRuleDescription"), 7, "left"),
        (tid("detectionEngineStepAboutRuleSeverity"), 8, "left"),
        (tid("detectionEngineStepAboutRuleTags"), 9, "left"),
    ])
    page.locator('[data-test-subj="about-continue"]').click(); settle(page, 4)
    iv = page.locator('[data-test-subj="detectionEngineStepScheduleRuleInterval"] input').first
    iv.fill("1"); time.sleep(0.5)
    fr = page.locator('[data-test-subj="detectionEngineStepScheduleRuleFrom"] input').first
    fr.fill("5"); time.sleep(1)
    shoot(page, lab, "04-schedule-rule", [
        (tid("detectionEngineStepScheduleRuleInterval"), 10, "left"),
        (tid("detectionEngineStepScheduleRuleFrom"), 11, "left"),
    ], scroll_to=tid("detectionEngineStepScheduleRuleInterval"))
    page.locator('[data-test-subj="schedule-continue"]').click(); settle(page, 4)
    shoot(page, lab, "05-create-enable", [(tid("create-enable"), 12, "left")], scroll_to=tid("create-enable"))
    page.locator('[data-test-subj="create-enable"]').click(); settle(page, 8)
    page.set_viewport_size({"width": 1600, "height": 900})


def lab06(page):
    lab = "LAB-ELK-06"
    page.goto(BASE + "/app/security/rules", wait_until="domcontentloaded"); settle(page, 8)
    shoot(page, lab, "06-rules", [
        (("role", "link", "SSH brute force: aynı IP'den 5+ başarısız giriş"), 13, "right"),
        (("role", "link", "Web saldırısı: dizin atlatma, gizli dosya veya SQL injection"), None, "right"),
    ])
    page.goto(BASE + "/app/security/alerts", wait_until="domcontentloaded"); settle(page, 10)
    shoot(page, lab, "07-alerts", [
        (("css", 'xpath=//*[normalize-space(text())="Alerts by name"]/ancestor::*[contains(@class,"euiPanel")][1]'), 14, "down"),
    ])


def lab07(page):
    lab = "LAB-ELK-07"
    page.goto(BASE + "/app/management/data/index_lifecycle_management/policies", wait_until="domcontentloaded"); settle(page, 5)
    shoot(page, lab, "01-ilm-policy", [(("css", 'tr:has-text("ilm-demo")'), 1, "down")])
    page.goto(BASE + "/app/management/data/index_management/indices", wait_until="domcontentloaded"); settle(page, 5)
    sb = page.get_by_placeholder("Search").first
    sb.fill("ilm-demo"); page.keyboard.press("Enter"); settle(page, 3)
    shoot(page, lab, "02-index-management", [
        (("css", 'input[placeholder="Search"]'), 2, "down"),
        (("union", ("css", 'tr:has-text("ilm-demo-000001")'), ("css", 'tr:has-text("ilm-demo-000002")')), 3, "left"),
    ])


FLOWS = {"lab07": lab07, "lab01": lab01, "lab03": lab03, "lab05": lab05, "lab06rule": lab06_create_rule, "lab06": lab06}

if __name__ == "__main__":
    names = sys.argv[1:] or list(FLOWS)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        page = b.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=SCALE)
        login(page)
        for n in names:
            FLOWS[n](page)
        b.close()
