(function(){
  const btn=document.querySelector('[data-menu]');
  const nav=document.querySelector('.navlinks');
  if(btn&&nav){btn.addEventListener('click',()=>{nav.classList.toggle('open');btn.setAttribute('aria-expanded',nav.classList.contains('open')?'true':'false')})}
  const revealEls=[...document.querySelectorAll('.reveal')];
  if('IntersectionObserver' in window){
    const io=new IntersectionObserver(entries=>{entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-visible');io.unobserve(e.target)}})},{threshold:.14});
    revealEls.forEach(el=>io.observe(el));
  }else{revealEls.forEach(el=>el.classList.add('is-visible'))}
  window.calcFee=function(){
    const q=id=>document.getElementById(id);
    if(!q('plan')) return;
    const plan=Number(q('plan').value||0);
    const people=Math.max(1, Number(q('people').value||1));
    const subsidy=Number(q('subsidy').value||0);
    const waiver=Number(q('waiver').value||0);
    const kit=Number(q('kit').value||0);
    const battery=Number(q('battery').value||0);
    const kitQty=Math.max(1, Number(q('kitQty')?.value||1));
    const tuition = waiver ? 0 : Math.max(0, plan-subsidy)*people;
    const materials = kit*kitQty + battery*kitQty;
    const total=tuition+materials;
    const comma=n=>Math.round(n).toLocaleString('zh-TW');
    const totalEl=q('total'); const detailEl=q('detail');
    if(totalEl) totalEl.textContent=comma(total)+' 元';
    if(detailEl){
      let d=waiver?'低收入或清寒生：學費免費':`學費：(${comma(plan)} − ${comma(subsidy)}) × ${people} 人`;
      const add=[]; if(kit) add.push(`未組裝機體套件 ${comma(kit)} × ${kitQty}`); if(battery) add.push(`2S 電池與充電器 ${comma(battery)} × ${kitQty}`);
      detailEl.textContent=d+(add.length?'；加購：'+add.join('、'):'');
    }
  };
  document.querySelectorAll('[data-calc]').forEach(el=>el.addEventListener('input',window.calcFee));
  window.calcFee();
  const form=document.querySelector('[data-register-form]');
  if(form){form.addEventListener('submit',ev=>{ev.preventDefault();document.querySelector('.toast')?.classList.add('show');})}
})();
