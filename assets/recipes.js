(() => {
  const lang = document.documentElement.lang === 'ko' ? 'ko' : 'en';
  const list = document.querySelector('[data-recipe-list]');
  const input = document.querySelector('[data-recipe-search]');
  let posts = [];
  const decode = (value) => { const el=document.createElement('textarea'); el.innerHTML=value; return el.value; };
  const detailUrl = (post) => `${lang === 'ko' ? '/ko' : ''}/recipe/?slug=${encodeURIComponent(post.slug)}`;
  const render = (items) => {
    if (!items.length) { list.innerHTML=`<p class="empty-state">${lang==='ko'?'검색 결과가 없습니다.':'No recipes found.'}</p>`; return; }
    list.innerHTML=items.map((post,index)=>`<a class="recipe-row" href="${detailUrl(post)}"><span class="number">${String(index+1).padStart(2,'0')}</span><div><h2>${decode(post.title)}</h2><p>${decode(post.excerpt).slice(0,150)}</p></div><time>${post.date}</time><b>↗</b></a>`).join('');
  };
  fetch('/assets/data/posts.json').then(r=>r.json()).then(data=>{ posts=data.filter(post=>post.language===lang); render(posts); document.querySelector('[data-recipe-count]').textContent=posts.length; }).catch(()=>{ list.innerHTML=`<p class="empty-state">${lang==='ko'?'레시피를 불러오지 못했습니다.':'Recipes could not be loaded.'}</p>`; });
  input?.addEventListener('input',()=>{ const q=input.value.trim().toLowerCase(); render(posts.filter(post=>decode(post.title).toLowerCase().includes(q)||decode(post.excerpt).toLowerCase().includes(q))); });
})();
