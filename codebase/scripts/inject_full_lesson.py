import sys
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]
CODEBASE = REPO / "codebase"
BACKEND_DATA = CODEBASE / "backend" / "Data" / "transcript"

# Hàm chunking từ build_local_data
sys.path.insert(0, str(CODEBASE / "backend"))
from app.chunking import parse_transcript_file

def inject():
    target_md = BACKEND_DATA / "transcript-06-clean.md"
    paras = parse_transcript_file(target_md)
    if not paras:
        print("No paras found")
        return
    
    sections = []
    current_sec = ""
    for p in paras:
        sec = p.section or "Tổng quan"
        if sec not in sections:
            sections.append(sec)
    
    # 1. Update index.html
    html_file = CODEBASE / "mock" / "index.html"
    html_content = html_file.read_text(encoding="utf-8")
    
    # Create the new lesson body
    body_html = '<div class="lesson-body" id="lessonBody">\n'
    last_sec = ""
    for p in paras:
        if p.section != last_sec:
            if last_sec != "":
                body_html += f'  <br/>\n'
            body_html += f'  <h3>{p.section or "Tổng quan"}</h3>\n'
            last_sec = p.section
            
        body_html += f'  <p>{p.text} <span class="src">[{p.id}]</span></p>\n'
    
    body_html += '  <p id="tooLong" class="too-long" hidden>Đoạn chọn quá dài để đánh dấu.</p>\n</div>'
    
    # Replace in index.html
    html_content = re.sub(r'<div class="lesson-body" id="lessonBody">.*?</div>', body_html, html_content, flags=re.DOTALL)
    html_file.write_text(html_content, encoding="utf-8")
    
    # 2. Update app.js sidebar
    app_js = CODEBASE / "mock" / "js" / "app.js"
    js_content = app_js.read_text(encoding="utf-8")
    
    sidebar_items = "const items = [\n"
    for s in sections:
        state = '"active"' if s == sections[0] else '""'
        sidebar_items += f'      [`{s}`, {state}],\n'
    sidebar_items += "    ];"
    
    js_content = re.sub(r'const items = \[.*?\];', sidebar_items, js_content, flags=re.DOTALL)
    app_js.write_text(js_content, encoding="utf-8")
    
    # 3. Update content.js for referenced_ids
    content_js = CODEBASE / "mock" / "js" / "content.js"
    cjs = content_js.read_text(encoding="utf-8")
    # append all ids as a comment so build_local_data picks them up
    ids = " ".join([p.id for p in paras])
    if "/* INJECTED IDS:" not in cjs:
        cjs += f"\n\n/* INJECTED IDS:\n{ids}\n*/\n"
    else:
        cjs = re.sub(r'/\* INJECTED IDS:.*?\*/', f'/* INJECTED IDS:\n{ids}\n*/', cjs, flags=re.DOTALL)
    content_js.write_text(cjs, encoding="utf-8")
    print("Injected successfully!")

if __name__ == "__main__":
    inject()
