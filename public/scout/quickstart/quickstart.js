(function(){
  "use strict";
  const tabs=[...document.querySelectorAll('[data-tab]')];
  const panels=[...document.querySelectorAll(".codepanel")];
  const copy=document.getElementById("copy-code");
  const theme=document.getElementById("theme-toggle");
  function select(tab){
    tabs.forEach(t=>{const active=t===tab;t.classList.toggle("active",active);t.setAttribute("aria-selected",String(active));t.tabIndex=active?0:-1;});
    panels.forEach(p=>{p.hidden=p.id!=="panel-"+tab.dataset.tab;});
  }
  tabs.forEach((tab,index)=>{tab.addEventListener("click",()=>select(tab));
    tab.addEventListener("keydown",e=>{
      if(!["ArrowLeft","ArrowRight","Home","End"].includes(e.key))return;
      e.preventDefault();
      const next=e.key==="Home"?0:e.key==="End"?tabs.length-1:
        (index+(e.key==="ArrowRight"?1:tabs.length-1))%tabs.length;
      select(tabs[next]);tabs[next].focus();
    });
  });
  copy.addEventListener("click",async()=>{
    const active=panels.find(p=>!p.hidden);
    const value=active?.querySelector("code")?.textContent;
    if(!value)return;
    try {
      if(!navigator.clipboard?.writeText)throw Error("Clipboard unavailable");
      await navigator.clipboard.writeText(value);
      copy.textContent="Copied!";
    }catch(_){copy.textContent="Select text to copy";}
  });
  theme.addEventListener("click",()=>{
    const next=document.documentElement.dataset.theme==="dark"?"light":"dark";
    document.documentElement.dataset.theme=next;
    theme.setAttribute("aria-label","Switch to "+(next==="dark"?"light":"dark")+" theme");
    try{localStorage.setItem("scout-quickstart-theme",next);}catch(_){}
  });
  try{const saved=localStorage.getItem("scout-quickstart-theme");
    if(saved==="light"||saved==="dark")document.documentElement.dataset.theme=saved;
  }catch(_){}
  theme.setAttribute("aria-label","Switch to "+(document.documentElement.dataset.theme==="dark"?"light":"dark")+" theme");
})();