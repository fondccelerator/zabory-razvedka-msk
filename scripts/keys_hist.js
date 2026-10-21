await new Promise(r=>setTimeout(r,4500));
const root=[...document.querySelectorAll('div')].find(d=>d.__vue_app__); const found=[]; const seen=new Set();
function walk(v,depth){ if(!v||depth>400||seen.has(v)) return; seen.add(v); if(v.component){ const c=v.component; if(c.props&&c.props.data&&c.props.data.datasets) found.push(c.props.data); walk(c.subTree,depth+1);} if(Array.isArray(v.children)) v.children.forEach(ch=>walk(ch,depth+1)); if(v.suspense) walk(v.suspense.activeBranch,depth+1);}
walk(root._vnode,0);
const t=document.body.innerText; const m=t.match(/Частотность\s*\n?\s*([\d\s]+)\n[\s\S]{0,40}?"!Частотность"\s*\n?\s*([\d\s—]+)\n[\s\S]{0,60}?Последняя проверка:\s*([\d.]+)/);
const d=found[0];
JSON.stringify({q:decodeURIComponent(new URL(location.href).searchParams.get('domain')||''), cur:m?[m[1].trim(),m[2].trim(),m[3]]:t.slice(0,80), h:d?d.labels.map((l,i)=>l+'='+d.datasets[0].data[i]+'/'+d.datasets[1].data[i]).join(';'):'нет графика'})
