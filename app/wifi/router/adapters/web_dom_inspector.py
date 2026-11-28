"""Chromium WebEngine DOM inspection & automation fallback for local router admin portals.

Uses PySide6 QtWebEngineWidgets offscreen DOM inspection rather than screenshot scraping:
- Strictly validates local-only router URLs (RFC1918 / loopback for tests).
- Discovers real login forms, navigation menus, tabs, submenus, expandable sections, and
  saved DOM input/select/checkbox/table values.
- Never brute-forces credentials, bypasses auth, or clicks destructive reset/reboot/factory buttons.
"""

from __future__ import annotations

import ipaddress
import json
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.wifi.router.credentials import validate_local_router_url


@dataclass
class DomPageExtract:
    url: str
    title: str
    section: str = ""
    submenu: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)
    tables: List[List[str]] = field(default_factory=list)
    menu_links: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class DomInspectionSessionResult:
    available: bool
    authenticated: bool = False
    base_url: str = ""
    login_form_detected: bool = False
    pages: List[DomPageExtract] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


_DESTRUCTIVE_KEYWORDS = (
    "reboot",
    "restart",
    "reset",
    "factory",
    "default",
    "restore default",
    "delete all",
    "upgrade",
    "firmware upload",
    "logout",
    "sign out",
    "shutdown",
    "إعادة تشغيل",
    "ضبط المصنع",
    "تسجيل الخروج",
)

_EXTRACT_DOM_JS = r"""
(() => {
  function collectDoc(doc, prefix) {
    const out = { fields: {}, tables: [], menu: [], forms: [] };
    if (!doc) return out;
    const inputs = doc.querySelectorAll('input, select, textarea');
    inputs.forEach((el, idx) => {
      const name = (el.name || el.id || el.getAttribute('aria-label') || ('field_' + idx)).trim();
      const t = (el.type || el.tagName || '').toLowerCase();
      let labelText = '';
      if (el.id) {
        const lbl = doc.querySelector('label[for="' + CSS.escape(el.id) + '"]');
        if (lbl) labelText = (lbl.innerText || '').trim();
      }
      if (!labelText) {
        const row = el.closest('tr');
        if (row) {
          const th = row.querySelector('th, td:first-child');
          if (th && !th.contains(el)) labelText = (th.innerText || '').trim();
        }
      }
      if (t === 'password') {
        out.fields[prefix + name] = { value: '[REDACTED]', type: 'password', disabled: !!el.disabled, label: labelText };
        return;
      }
      if (t === 'checkbox' || t === 'radio') {
        if (t === 'radio' && !el.checked) return;
        out.fields[prefix + name] = { value: !!el.checked, type: t, disabled: !!el.disabled, label: labelText };
      } else if (el.tagName.toLowerCase() === 'select') {
        const opt = el.options && el.selectedIndex >= 0 ? el.options[el.selectedIndex] : null;
        out.fields[prefix + name] = {
          value: opt ? (opt.text || el.value) : el.value,
          raw: el.value,
          type: 'select',
          disabled: !!el.disabled,
          label: labelText
        };
      } else if (t !== 'button' && t !== 'submit' && t !== 'hidden') {
        out.fields[prefix + name] = { value: el.value || '', type: t, disabled: !!el.disabled, label: labelText };
      }
    });

    doc.querySelectorAll('table').forEach(tbl => {
      const rows = [];
      tbl.querySelectorAll('tr').forEach(tr => {
        const cells = Array.from(tr.querySelectorAll('th, td')).map(c => (c.innerText || '').trim()).filter(Boolean);
        if (cells.length) rows.push(cells);
      });
      if (rows.length) out.tables.push(...rows.slice(0, 40));
    });

    doc.querySelectorAll('a, li, button, [role="tab"], [role="menuitem"]').forEach(el => {
      const txt = (el.innerText || el.title || '').trim();
      const href = el.getAttribute('href') || '';
      const id = el.id || '';
      if (txt && txt.length <= 64) {
        out.menu.push({ text: txt, href: href, id: id, tag: el.tagName.toLowerCase() });
      }
    });

    const pwInput = doc.querySelector('input[type="password"]');
    if (pwInput) {
      out.forms.push({ hasPassword: true, action: (pwInput.form && pwInput.form.action) || '' });
    }
    return out;
  }

  const root = collectDoc(document, '');
  try {
    const frames = document.querySelectorAll('iframe, frame');
    frames.forEach((fr, fi) => {
      try {
        if (fr.contentDocument) {
          const sub = collectDoc(fr.contentDocument, 'frame' + fi + '.');
          Object.assign(root.fields, sub.fields);
          root.tables.push(...sub.tables);
          root.menu.push(...sub.menu);
          root.forms.push(...sub.forms);
        }
      } catch (e) {}
    });
  } catch (e) {}
  return JSON.stringify({
    url: location.href,
    title: document.title || '',
    fields: root.fields,
    tables: root.tables.slice(0, 80),
    menu: root.menu.slice(0, 80),
    hasLoginForm: root.forms.length > 0
  });
})()
"""


class RouterWebDomInspector:
    """Safely inspects router admin HTML/JS pages using QtWebEngine offscreen DOM evaluation."""

    @staticmethod
    def is_available() -> bool:
        try:
            import PySide6.QtWebEngineCore  # noqa: F401
            import PySide6.QtWebEngineWidgets  # noqa: F401
            return True
        except Exception:
            return False

    @staticmethod
    def is_safe_navigation_target(text: str, href: str) -> bool:
        low = f"{text} {href}".lower()
        if any(k in low for k in _DESTRUCTIVE_KEYWORDS):
            return False
        if href.startswith("http://") or href.startswith("https://"):
            try:
                parsed = urllib.parse.urlparse(href)
                addr = ipaddress.ip_address(parsed.hostname or "")
                return bool(addr.is_private or addr.is_loopback or addr.is_link_local)
            except Exception:
                return False
        return True

    def inspect_portal(
        self,
        *,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        allow_loopback: bool = False,
        max_pages: int = 8,
        timeout_ms: int = 4500,
    ) -> DomInspectionSessionResult:
        """Load the local portal in an offscreen QWebEnginePage (main thread required).

        If called on a non-Qt thread or when QApplication/QtWebEngine is unavailable,
        gracefully reports availability status without crashing.
        """
        validate_local_router_url(base_url, allow_loopback=allow_loopback)
        if not self.is_available():
            return DomInspectionSessionResult(
                available=False,
                base_url=base_url,
                notes=["PySide6 QtWebEngineWidgets is unavailable in this runtime."],
            )

        from PySide6.QtCore import QEventLoop, QTimer, QUrl, QThread
        from PySide6.QtWidgets import QApplication
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

        app = QApplication.instance()
        if app is None or QThread.currentThread() != app.thread():
            return DomInspectionSessionResult(
                available=True,
                base_url=base_url,
                notes=[
                    "Web DOM inspection skipped because no Qt GUI thread owns QApplication here; HTTP/API inspection remains primary."
                ],
            )

        profile = QWebEngineProfile(app)
        page = QWebEnginePage(profile)
        result = DomInspectionSessionResult(available=True, base_url=base_url)

        def _ignore_local_cert(err: Any) -> bool:
            try:
                u = err.url().host()
                addr = ipaddress.ip_address(u)
                return bool(addr.is_private or addr.is_loopback or addr.is_link_local)
            except Exception:
                return False

        # Accept self-signed TLS certs ONLY on verified private/local router IPs
        if hasattr(page, "certificateError"):
            page.certificateError.connect(lambda err: err.acceptCertificate() if _ignore_local_cert(err) else err.rejectCertificate())

        def _load_and_wait(url: str) -> bool:
            loop = QEventLoop()
            loaded = {"ok": False}

            def _on_done(ok: bool) -> None:
                loaded["ok"] = bool(ok)
                if loop.isRunning():
                    loop.quit()

            page.loadFinished.connect(_on_done)
            QTimer.singleShot(timeout_ms, loop.quit)
            page.load(QUrl(url))
            loop.exec()
            try:
                page.loadFinished.disconnect(_on_done)
            except Exception:
                pass
            return loaded["ok"]

        def _run_js(script: str) -> Any:
            loop = QEventLoop()
            box: Dict[str, Any] = {"val": None}

            def _cb(res: Any) -> None:
                box["val"] = res
                if loop.isRunning():
                    loop.quit()

            QTimer.singleShot(1800, loop.quit)
            page.runJavaScript(script, _cb)
            loop.exec()
            return box["val"]

        try:
            if not _load_and_wait(base_url):
                result.notes.append(f"QtWebEngine could not load {base_url} within {timeout_ms}ms.")
                return result

            raw_json = _run_js(_EXTRACT_DOM_JS)
            if isinstance(raw_json, str):
                data = json.loads(raw_json)
                result.login_form_detected = bool(data.get("hasLoginForm"))
                result.pages.append(
                    DomPageExtract(
                        url=data.get("url") or base_url,
                        title=data.get("title") or "Root",
                        section="Login / Entry",
                        fields=data.get("fields") or {},
                        tables=data.get("tables") or [],
                        menu_links=data.get("menu") or [],
                    )
                )

                # Single-attempt credential fill if user explicitly supplied credentials and login form exists
                if result.login_form_detected and username is not None and password is not None:
                    login_js = (
                        "(() => {"
                        "const pw = document.querySelector('input[type=\"password\"]') || "
                        "(document.querySelector('iframe,frame')?.contentDocument?.querySelector('input[type=\"password\"]'));"
                        "if (!pw) return 'no_pw';"
                        "const doc = pw.ownerDocument;"
                        "const usr = doc.querySelector('input[type=\"text\"], input[name*=\"user\" i], input[id*=\"user\" i]');"
                        f"if (usr) {{ usr.value = {json.dumps(username)}; usr.dispatchEvent(new Event('input', {{bubbles:true}})); }}"
                        f"pw.value = {json.dumps(password)}; pw.dispatchEvent(new Event('input', {{bubbles:true}}));"
                        "const btn = doc.querySelector('button[type=\"submit\"], input[type=\"submit\"], button[id*=\"login\" i]');"
                        "if (btn) btn.click(); else if (pw.form) pw.form.submit();"
                        "return 'submitted';"
                        "})()"
                    )
                    sub_status = _run_js(login_js)
                    if sub_status == "submitted":
                        loop_wait = QEventLoop()
                        page.loadFinished.connect(loop_wait.quit)
                        QTimer.singleShot(min(2200, timeout_ms), loop_wait.quit)
                        loop_wait.exec()
                        try:
                            page.loadFinished.disconnect(loop_wait.quit)
                        except Exception:
                            pass
                        post_raw = _run_js(_EXTRACT_DOM_JS)
                        if isinstance(post_raw, str):
                            pdata = json.loads(post_raw)
                            if not pdata.get("hasLoginForm"):
                                result.authenticated = True
                                result.pages.append(
                                    DomPageExtract(
                                        url=pdata.get("url") or base_url,
                                        title=pdata.get("title") or "Home",
                                        section="Authenticated Home",
                                        fields=pdata.get("fields") or {},
                                        tables=pdata.get("tables") or [],
                                        menu_links=pdata.get("menu") or [],
                                    )
                                )
                                # Visit bounded safe menu links and safe interactive tabs
                                visited = {pdata.get("url")}
                                clicked_labels = set()
                                for item in (pdata.get("menu") or [])[: max_pages * 2]:
                                    if len(result.pages) >= max_pages:
                                        break
                                    href = str(item.get("href") or "")
                                    txt = str(item.get("text") or "")
                                    el_id = str(item.get("id") or "")
                                    tag = str(item.get("tag") or "")
                                    if not self.is_safe_navigation_target(txt, href):
                                        continue
                                    if not href or href.startswith("#") or "javascript:" in href.lower():
                                        if txt in clicked_labels or tag not in ("a", "button", "li"):
                                            continue
                                        clicked_labels.add(txt)
                                        click_js = (
                                            "(() => {"
                                            f"const id = {json.dumps(el_id)}; const t = {json.dumps(txt)};"
                                            "let el = id ? document.getElementById(id) : null;"
                                            "if (!el) { el = Array.from(document.querySelectorAll('a,button,li,[role=\"tab\"]')).find(x => (x.innerText||'').trim() === t); }"
                                            "if (el) { el.click(); return 'clicked'; } return 'miss';"
                                            "})()"
                                        )
                                        if _run_js(click_js) == "clicked":
                                            sub_wait = QEventLoop()
                                            QTimer.singleShot(450, sub_wait.quit)
                                            sub_wait.exec()
                                            tab_raw = _run_js(_EXTRACT_DOM_JS)
                                            if isinstance(tab_raw, str):
                                                sdata = json.loads(tab_raw)
                                                result.pages.append(
                                                    DomPageExtract(
                                                        url=sdata.get("url") or base_url,
                                                        title=sdata.get("title") or txt,
                                                        section=txt,
                                                        fields=sdata.get("fields") or {},
                                                        tables=sdata.get("tables") or [],
                                                        menu_links=sdata.get("menu") or [],
                                                    )
                                                )
                                        continue
                                    full = urllib.parse.urljoin(base_url + "/", href)
                                    if full in visited:
                                        continue
                                    visited.add(full)
                                    if _load_and_wait(full):
                                        sub_raw = _run_js(_EXTRACT_DOM_JS)
                                        if isinstance(sub_raw, str):
                                            sdata = json.loads(sub_raw)
                                            result.pages.append(
                                                DomPageExtract(
                                                    url=full,
                                                    title=sdata.get("title") or txt,
                                                    section=txt,
                                                    fields=sdata.get("fields") or {},
                                                    tables=sdata.get("tables") or [],
                                                    menu_links=sdata.get("menu") or [],
                                                )
                                            )
        finally:
            try:
                page.deleteLater()
                profile.deleteLater()
            except Exception:
                pass
        return result
