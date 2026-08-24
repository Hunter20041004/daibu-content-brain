from dataclasses import dataclass
from typing import Mapping

import streamlit as st


TEMPLATE_HTML = """
<div class="template-editor" data-role="template-editor">
  <header data-role="version-bar"></header>
  <nav data-role="page-rail" aria-label="模板頁面"></nav>
  <main data-role="canvas-panel">
    <div class="canvas-toolbar"></div>
    <div class="template-stage" data-role="template-canvas">
      <div class="template-document"></div><div class="overlay-layer"></div>
    </div>
    <p class="mobile-notice">請改用桌面寬度調整模板；手機仍可檢視版本與預覽。</p>
  </main>
  <aside data-role="property-panel"></aside>
</div>
"""

TEMPLATE_CSS = """
:host { --ink:#173d4d; --ink-deep:#102f3d; --teal:#2f7c87; --cyan:#86ccd4; --cyan-soft:#dceff1; --peach:#ec9870; --coral:#ec9870; --paper:#fafbf8; --ice:#edf6f7; --line:#b8d7dd; --muted:#61747d; display:block; color:var(--ink-deep); font-family:"LINE Seed TW","PingFang TC",sans-serif; }
* { box-sizing:border-box; }
.template-editor { display:grid; grid-template-columns:120px minmax(480px,1fr) 220px; grid-template-rows:auto minmax(680px,auto); border:1px solid var(--line); background:var(--paper); overflow:hidden; }
[data-role="version-bar"] { grid-column:1/-1; display:flex; align-items:center; justify-content:space-between; min-height:64px; padding:12px 18px; border-bottom:1px solid var(--line); background:var(--ink); color:white; }
.preview-sync-error { margin:0 0 0 12px; color:var(--peach); font-size:12px; font-weight:800; }
[data-role="page-rail"] { display:flex; flex-direction:column; gap:3px; padding:12px 8px; border-right:1px solid var(--line); background:var(--ice); }
button { font:inherit; }
[data-role="page-rail"] button { min-height:48px; border:0; border-left:3px solid transparent; background:transparent; color:#61747d; text-align:left; font-size:12px; font-weight:700; }
[data-role="page-rail"] button[aria-current="page"] { border-left-color:var(--peach); background:white; color:var(--ink); }
[data-role="canvas-panel"] { min-width:0; padding:18px; background:#dfecef; }
.canvas-toolbar { display:flex; gap:8px; margin-bottom:12px; }
.canvas-toolbar button,[data-role="version-bar"] button { min-height:38px; padding:0 14px; border:1px solid currentColor; border-radius:0; background:transparent; color:inherit; font-weight:800; }
.template-stage { position:relative; width:min(100%,540px); aspect-ratio: 4 / 5; margin:auto; overflow:hidden; background:white; box-shadow:0 18px 42px rgba(16,47,61,.18); }
.template-document { position:absolute; inset:0 auto auto 0; width:1080px; height:1350px; transform-origin:top left; }
.overlay-layer { position:absolute; inset:0; pointer-events:none; }
.selection-box { position:absolute; border:2px solid var(--teal); pointer-events:auto; cursor:move; transition:border-color 120ms ease; }
.selection-box[data-collision="near"] { border-color:var(--peach); }
.selection-box[data-collision="hit"] { border-color:#b54232; }
.snap-guide { position:absolute; z-index:0; background:var(--cyan); pointer-events:none; }
.snap-guide--x { top:0; bottom:0; width:1px; }
.snap-guide--y { right:0; left:0; height:1px; }
.resize-handle { position:absolute; width:12px; height:12px; padding:0; border:2px solid white; border-radius:50%; background:var(--teal); transform:translate(-50%,-50%); }
.resize-handle:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible { outline:3px solid var(--peach); outline-offset:2px; }
[data-handle="n"]{left:50%;top:0}[data-handle="ne"]{left:100%;top:0}[data-handle="e"]{left:100%;top:50%}[data-handle="se"]{left:100%;top:100%}[data-handle="s"]{left:50%;top:100%}[data-handle="sw"]{left:0;top:100%}[data-handle="w"]{left:0;top:50%}[data-handle="nw"]{left:0;top:0}
[data-role="property-panel"] { padding:18px 14px; border-left:1px solid var(--line); background:white; }
.property-title { margin:0 0 16px; font-size:18px; }
.property-field { display:block; margin:0 0 12px; font-size:12px; font-weight:800; }
.property-field input,.property-field select { display:block; width:100%; min-height:38px; margin-top:5px; border:1px solid var(--line); border-radius:0; padding:6px 8px; color:var(--ink); background:var(--paper); }
.mobile-notice { display:none; color:var(--teal); font-weight:800; }
@media (max-width: 767px) { .template-editor { display:block; width:100%; } [data-role="version-bar"] button { display:none; } [data-role="page-rail"] { flex-direction:row; overflow-x:auto; border-right:0; border-bottom:1px solid var(--line); } [data-role="page-rail"] button { flex:0 0 104px; } [data-role="property-panel"],.canvas-toolbar,.overlay-layer { display:none; } [data-role="canvas-panel"] { padding:14px; } .mobile-notice { display:block; } .template-stage { width:100%; } }
"""

TEMPLATE_JS = r"""
const HANDLE_DIRECTIONS = ["n","ne","e","se","s","sw","w","nw"];
const GRID_PX = 8, SNAP_PX = 6, SAFE_MARGIN = 48, HISTORY_LIMIT = 50;
function clientDeltaToCanvas(delta, renderedWidth) { return delta * 1080 / renderedWidth; }
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function elementMap(state, pageType) { return state.present.pages[pageType].elements; }
function equal(a,b) { return JSON.stringify(a) === JSON.stringify(b); }
function clamp(value,min,max) { return Math.min(max,Math.max(min,value)); }
function nearestSnap(edges,targets) { let best=null; edges.forEach(edge=>targets.forEach(target=>{const distance=target-edge;if(Math.abs(distance)<=SNAP_PX&&(!best||Math.abs(distance)<Math.abs(best.distance)))best={distance,target};}));return best; }

export default function(component) {
  const {data,parentElement,setStateValue,setTriggerValue} = component;
  const root = parentElement.querySelector('[data-role="template-editor"]');
  const storageKey = `daibu-template-${data.themeId}-${data.versionId}`;
  const stored = JSON.parse(sessionStorage.getItem(storageKey) || "null");
  const state = stored || {past:[],present:clone(data.layout),future:[],selected:null,dirty:false,guides:[]};
  state.guides=[];
  let activePointer=null;
  const persist = () => sessionStorage.setItem(storageKey, JSON.stringify(state));
  const mark = next => { if (equal(state.present,next)) return; state.past.push(clone(state.present)); if(state.past.length>HISTORY_LIMIT)state.past.shift(); state.present=next; state.future=[]; state.dirty=!equal(state.present,data.layout); setStateValue("dirty",state.dirty); persist(); render(); };
  const undo = () => { if(!state.past.length)return; state.future.unshift(clone(state.present)); state.present=state.past.pop(); state.dirty=!equal(state.present,data.layout); setStateValue("dirty",state.dirty); persist(); render(); };
  const redo = () => { if(!state.future.length)return; state.past.push(clone(state.present)); state.present=state.future.shift(); state.dirty=!equal(state.present,data.layout); setStateValue("dirty",state.dirty); persist(); render(); };
  function applyWorkingLayout() {
    const missing=[];
    const items=elementMap(state,data.pageType);
    const doc=root.querySelector('.template-document');
    Object.entries(items).forEach(([elementId,item])=>{
      const element=doc.querySelector(`[data-layout-id="${elementId}"]`);
      if(!element){missing.push(elementId);return;}
      const descriptor=data.elements.find(entry=>entry.elementId===elementId);
      const values={left:`${item.x}px`,top:`${item.y}px`,width:`${item.w}px`,height:`${item.h}px`};
      if(descriptor?.kind==='text'){
        values['font-size']=`${item.font_size}px`;
        values['text-align']=item.text_align;
      }
      Object.entries(values).forEach(([property,value])=>element.style.setProperty(property,value,"important"));
    });
    return missing;
  }
  function render() {
    const doc=root.querySelector('.template-document'); doc.innerHTML=data.previewHtml;
    const missing = applyWorkingLayout();
    const versionBar=root.querySelector('[data-role="version-bar"]'); versionBar.replaceChildren();
    const title=document.createElement('strong'); title.textContent=`${data.themeName}｜v${data.versionNo}${state.dirty?' · 未儲存':''}`;
    const syncError=data.previewSyncError||(missing.length?`預覽缺少版面元素：${missing.join('、')}`:'');
    const save=document.createElement('button'); save.textContent='儲存為新版本'; save.disabled=!state.dirty||Boolean(syncError); save.addEventListener('click',()=>setTriggerValue("saveLayout",{baseVersionId:data.versionId,layout:state.present})); versionBar.append(title,save);
    if(syncError){const alert=document.createElement('p');alert.className='preview-sync-error';alert.setAttribute('role','alert');alert.textContent=syncError;versionBar.append(alert);}
    const rail=root.querySelector('[data-role="page-rail"]'); rail.replaceChildren(); data.pages.forEach((item,index)=>{const b=document.createElement('button');b.textContent=`${String(index+1).padStart(2,'0')} ${item.label}`;b.setAttribute('aria-current',item.pageType===data.pageType?'page':'false');b.onclick=()=>setTriggerValue('requestPage',item.pageType);rail.append(b);});
    const toolbar=root.querySelector('.canvas-toolbar'); toolbar.replaceChildren();
    [['復原',undo],['重做',redo]].forEach(([label,fn])=>{const b=document.createElement('button');b.textContent=label;b.setAttribute('aria-label',label);b.onclick=fn;toolbar.append(b);});
    const reset=document.createElement('button');reset.textContent='重設本頁';reset.setAttribute('aria-label','重設本頁');reset.onclick=()=>{const next=clone(state.present);next.pages[data.pageType]=clone(data.layout.pages[data.pageType]);mark(next);};toolbar.append(reset);
    const stage=root.querySelector('.template-stage'); const scale=stage.clientWidth/1080; doc.style.transform=`scale(${scale})`;
    doc.querySelectorAll('[data-layout-id]').forEach(el=>{el.tabIndex=0;el.onclick=e=>{e.preventDefault();e.stopPropagation();state.selected=el.dataset.layoutId;persist();renderSelection();renderProperties();};el.onkeydown=e=>{if(e.key==='Enter'){state.selected=el.dataset.layoutId;renderSelection();renderProperties();} if(state.selected===el.dataset.layoutId&&e.key.startsWith('Arrow')){e.preventDefault();const amount=e.shiftKey?10:1;const next=clone(state.present);const item=next.pages[data.pageType].elements[state.selected];if(e.key==='ArrowLeft')item.x-=amount;if(e.key==='ArrowRight')item.x+=amount;if(e.key==='ArrowUp')item.y-=amount;if(e.key==='ArrowDown')item.y+=amount;mark(next);}};});
    renderSelection(); renderProperties();
  }
  function collisionState(selected,item){const descriptor=data.elements.find(entry=>entry.elementId===selected);if(!descriptor||descriptor.collision!=='avoid')return '';let result='';Object.entries(elementMap(state,data.pageType)).forEach(([id,other])=>{if(id===selected)return;const rule=data.elements.find(entry=>entry.elementId===id);if(!rule||rule.collision!=='avoid')return;const overlapX=item.x<other.x+other.w&&item.x+item.w>other.x;const overlapY=item.y<other.y+other.h&&item.y+item.h>other.y;if(overlapX&&overlapY)result='hit';else if(result!=='hit'){const gapX=Math.max(other.x-(item.x+item.w),item.x-(other.x+other.w),0);const gapY=Math.max(other.y-(item.y+item.h),item.y-(other.y+other.h),0);if((overlapX&&gapY<=12)||(overlapY&&gapX<=12))result='near';}});return result;}
  function renderSelection(){const overlay=root.querySelector('.overlay-layer');overlay.replaceChildren();state.guides.forEach(guide=>{const line=document.createElement('div');line.className=`snap-guide snap-guide--${guide.axis}`;if(guide.axis==='x')line.style.left=`${guide.value/10.8}%`;else line.style.top=`${guide.value/13.5}%`;overlay.append(line);});if(!state.selected)return;const item=elementMap(state,data.pageType)[state.selected];if(!item)return;const box=document.createElement('div');box.className='selection-box';box.dataset.elementId=state.selected;box.dataset.collision=collisionState(state.selected,item);Object.assign(box.style,{left:`${item.x/10.8}%`,top:`${item.y/13.5}%`,width:`${item.w/10.8}%`,height:`${item.h/13.5}%`});
    HANDLE_DIRECTIONS.forEach(direction=>{const handle=document.createElement('button');handle.className='resize-handle';handle.dataset.handle=direction;handle.setAttribute('aria-label',`向 ${direction} 縮放`);handle.onpointerdown=e=>startPointer(e,direction);box.append(handle);});box.onpointerdown=e=>{if(!e.target.dataset.handle)startPointer(e,'move');};overlay.append(box);}
  function startPointer(event,direction){event.preventDefault();if(activePointer)return;event.currentTarget?.setPointerCapture?.(event.pointerId);const startX=event.clientX,startY=event.clientY,before=clone(state.present),original=clone(elementMap(state,data.pageType)[state.selected]),stage=root.querySelector('.template-stage'),descriptor=data.elements.find(item=>item.elementId===state.selected),minW=descriptor.minValues.w,minH=descriptor.minValues.h;
    const cleanup=()=>{window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);state.guides=[];activePointer=null;};
    const cancel=()=>{cleanup();state.present=before;applyWorkingLayout();renderSelection();renderProperties();};
    const move=e=>{let dx=clientDeltaToCanvas(e.clientX-startX,stage.clientWidth),dy=clientDeltaToCanvas(e.clientY-startY,stage.clientWidth);const next=clone(before),items=next.pages[data.pageType].elements,item=items[state.selected];state.guides=[];if(direction==='move'){item.x=clamp(Math.round((original.x+dx)/GRID_PX)*GRID_PX,0,data.canvas.width-item.w);item.y=clamp(Math.round((original.y+dy)/GRID_PX)*GRID_PX,0,data.canvas.height-item.h);const others=Object.entries(items).filter(([id])=>id!==state.selected).map(([,value])=>value),xTargets=[SAFE_MARGIN,data.canvas.width/2,data.canvas.width-SAFE_MARGIN],yTargets=[SAFE_MARGIN,data.canvas.height/2,data.canvas.height-SAFE_MARGIN];others.forEach(other=>{xTargets.push(other.x,other.x+other.w/2,other.x+other.w);yTargets.push(other.y,other.y+other.h/2,other.y+other.h);});const sx=nearestSnap([item.x,item.x+item.w/2,item.x+item.w],xTargets),sy=nearestSnap([item.y,item.y+item.h/2,item.y+item.h],yTargets);if(sx){item.x=clamp(item.x+sx.distance,0,data.canvas.width-item.w);state.guides.push({axis:'x',value:sx.target});}if(sy){item.y=clamp(item.y+sy.distance,0,data.canvas.height-item.h);state.guides.push({axis:'y',value:sy.target});}}else{const right=original.x+original.w,bottom=original.y+original.h;if(direction.includes('e'))item.w=clamp(Math.round((original.w+dx)/GRID_PX)*GRID_PX,minW,data.canvas.width-original.x);if(direction.includes('s'))item.h=clamp(Math.round((original.h+dy)/GRID_PX)*GRID_PX,minH,data.canvas.height-original.y);if(direction.includes('w')){item.x=clamp(Math.round((original.x+dx)/GRID_PX)*GRID_PX,0,right-minW);item.w=right-item.x;}if(direction.includes('n')){item.y=clamp(Math.round((original.y+dy)/GRID_PX)*GRID_PX,0,bottom-minH);item.h=bottom-item.y;}}state.present=next;applyWorkingLayout();renderSelection();renderProperties();};
    const up=()=>{cleanup();const after=clone(state.present);state.present=before;mark(after);};activePointer={cancel};window.addEventListener('pointermove',move);window.addEventListener('pointerup',up,{once:true});}
  function renderProperties(){const panel=root.querySelector('[data-role="property-panel"]');panel.replaceChildren();const heading=document.createElement('h3');heading.className='property-title';if(!state.selected){heading.textContent='選擇一個元素';panel.append(heading);return;}const descriptor=data.elements.find(item=>item.elementId===state.selected);heading.textContent=descriptor.label;panel.append(heading);const item=elementMap(state,data.pageType)[state.selected];descriptor.editableProperties.forEach(prop=>{const label=document.createElement('label');label.className='property-field';label.textContent={x:'X 位置',y:'Y 位置',w:'寬度',h:'高度',font_size:'字級',text_align:'對齊'}[prop];const input=prop==='text_align'?document.createElement('select'):document.createElement('input');let lower=null,upper=null;if(prop==='text_align'){['left','center','right'].forEach(value=>{const o=document.createElement('option');o.value=value;o.textContent={left:'靠左',center:'置中',right:'靠右'}[value];input.append(o);});}else{input.type='number';input.step='1';if(prop==='x'){lower=0;upper=data.canvas.width-item.w;}if(prop==='y'){lower=0;upper=data.canvas.height-item.h;}if(prop==='w'){lower=descriptor.minValues.w;upper=data.canvas.width-item.x;}if(prop==='h'){lower=descriptor.minValues.h;upper=data.canvas.height-item.y;}if(prop==='font_size'){lower=descriptor.minValues.font_size;upper=descriptor.maxValues.font_size;}input.min=String(lower);input.max=String(upper);}input.name=prop;input.value=item[prop];input.onchange=()=>{const next=clone(state.present);next.pages[data.pageType].elements[state.selected][prop]=prop==='text_align'?input.value:clamp(input.valueAsNumber,lower,upper);mark(next);};label.append(input);panel.append(label);});}
  window.onkeydown=e=>{if(e.key==='Escape'&&activePointer){e.preventDefault();activePointer.cancel();return;}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();e.shiftKey?redo():undo();}};
  requestAnimationFrame(render);
}
"""


@dataclass(frozen=True)
class TemplateEditorEvent:
    dirty: bool
    save_payload: Mapping[str, object] | None
    request_page: str | None = None


def mount_template_editor(payload: Mapping[str, object], *, key: str) -> TemplateEditorEvent:
    renderer = st.components.v2.component("daibu_carousel_template_editor", html=TEMPLATE_HTML, css=TEMPLATE_CSS, js=TEMPLATE_JS, isolate_styles=True)
    result = renderer(key=key, data=dict(payload), default={"dirty":False}, height="content", on_dirty_change=lambda:None, on_saveLayout_change=lambda:None, on_requestPage_change=lambda:None)
    if result is None:
        return TemplateEditorEvent(False,None)
    save=getattr(result,"saveLayout",None)
    return TemplateEditorEvent(bool(getattr(result,"dirty",False)),dict(save) if isinstance(save,Mapping) else None,getattr(result,"requestPage",None))
