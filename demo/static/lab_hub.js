(function(){
  'use strict';
  const root=document.querySelector('#s7lab'); if(!root)return;
  const search=document.querySelector('#s7lab-search');
  const buttons=[...root.querySelectorAll('.s7lab-rail button')];
  const tests=[...root.querySelectorAll('.s7lab-test')];
  const chapters=[...root.querySelectorAll('.s7lab-chapter')];
  const count=document.querySelector('#s7lab-count');
  let phase='all';
  function normalize(s){return (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();}
  function refresh(){
    const q=normalize(search.value.trim());let shown=0;
    tests.forEach(el=>{
      const passPhase=phase==='all'||phase===el.dataset.phase;
      const passSearch=normalize(el.dataset.search+' '+el.textContent).includes(q);
      const show=passPhase&&passSearch;
      el.hidden=!show;if(show)shown++;
    });
    chapters.forEach(el=>{el.hidden=![...el.querySelectorAll('.s7lab-test')].some(t=>!t.hidden);});
    count.textContent=shown+' '+(shown===1?'teste encontrado':'testes encontrados');
  }
  buttons.forEach(b=>b.addEventListener('click',()=>{
    phase=b.dataset.filter;
    buttons.forEach(v=>{v.classList.toggle('selected',v===b);v.setAttribute('aria-pressed',String(v===b));});
    refresh();
  }));
  search.addEventListener('input',refresh);
  const frame=document.querySelector('#s7lab-frame');
  const empty=document.querySelector('#s7lab-pane-empty');
  const title=document.querySelector('#s7lab-frame-title');
  const close=document.querySelector('#s7lab-close');
  root.querySelectorAll('.s7lab-preview').forEach(btn=>btn.addEventListener('click',()=>{
    const target=btn.dataset.url;
    // Only selected same-origin routes; never create browser-controlled proxies.
    if(!['/','/pairwise','/m2m','/m3/consent'].includes(target))return;
    const url=new URL(target,window.location.origin);
    url.searchParams.set('embed','1');
    frame.src=url.pathname+url.search;
    frame.hidden=false; empty.hidden=true;close.hidden=false;
    title.textContent=btn.dataset.name;
    if(window.innerWidth<1200)root.querySelector('.s7lab-pane').scrollIntoView({behavior:'smooth',block:'start'});
  }));
  close.addEventListener('click',()=>{frame.src='about:blank';frame.hidden=true;empty.hidden=false;close.hidden=true;title.textContent='Selecione um teste';});
  refresh();
})();
