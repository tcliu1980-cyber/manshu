const menuBtn = document.querySelector('[data-menu]');
const nav = document.querySelector('.navlinks');
if(menuBtn && nav){
  menuBtn.addEventListener('click',()=>{
    const open = nav.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', String(open));
  });
}
const group = document.querySelector('#groupType');
const subsidy = document.querySelector('#subsidy');
const kit = document.querySelector('#kit');
const battery = document.querySelector('#battery');
const result = document.querySelector('#calcResult');
function calc(){
  if(!group || !result) return;
  const tuition = Number(group.value||0);
  const sub = subsidy?.checked ? 1500 : 0;
  const kitFee = kit?.checked ? 2000 : 0;
  const batFee = battery?.checked ? 1000 : 0;
  const finalTuition = Math.max(0, tuition - sub);
  const total = finalTuition + kitFee + batFee;
  result.innerHTML = `估算每人費用：<b>NT$ ${total.toLocaleString('zh-TW')}</b><br><span class="small">課程費 ${finalTuition.toLocaleString('zh-TW')} + 加購材料 ${ (kitFee+batFee).toLocaleString('zh-TW') }。正式金額以學校公告與通知為準。</span>`;
}
[group,subsidy,kit,battery].forEach(el=>el&&el.addEventListener('change',calc));calc();
