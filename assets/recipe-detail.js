(() => {
  const lang = document.documentElement.lang === 'ko' ? 'ko' : 'en';
  const root = document.querySelector('[data-recipe-detail]');
  const slug = new URLSearchParams(location.search).get('slug');
  const slugAliases = { 'naengmyeon-kr': 'naengmyeon-2' };
  const requestedSlug = slugAliases[(slug || '').toLowerCase()] || slug;
  const decode = (value = '') => { const el = document.createElement('textarea'); el.innerHTML = value; return el.value; };
  const equivalentSlug = (a = '', b = '') => {
    try { return decodeURIComponent(a).toLowerCase() === decodeURIComponent(b).toLowerCase(); }
    catch { return a.toLowerCase() === b.toLowerCase(); }
  };
  const error = () => {
    const copy = lang === 'ko'
      ? ['레시피를 찾을 수 없습니다.', '레시피 목록으로 돌아가기']
      : ['This recipe could not be found.', 'Return to recipes'];
    root.innerHTML = `<div class="article-error"><p>${copy[0]}<br><a href="${lang === 'ko' ? '/ko' : ''}/recipes/">${copy[1]}</a></p></div>`;
  };
  const cleanContent = (html) => {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    doc.querySelectorAll('script, style, ins.adsbygoogle, .adsbygoogle, .wp-block-kadence-posts, .kb-posts, form').forEach(el => el.remove());
    return doc.body.innerHTML;
  };
  const localizeArticleLinks = (posts) => {
    root.querySelectorAll('.article-body a[href]').forEach(link => {
      try {
        const url = new URL(link.href, location.origin);
        if (url.hostname !== 'kfood.bumkok.com') return;
        const linkedSlug = url.pathname.replace(/^\/+|\/+$/g, '');
        const target = posts.find(post => equivalentSlug(post.slug, linkedSlug));
        if (!target) return;
        link.href = `${target.language === 'ko' ? '/ko' : ''}/recipe/?slug=${encodeURIComponent(target.slug)}`;
        link.removeAttribute('target');
      } catch {}
    });
  };
  if (!slug) { error(); return; }
  fetch('/assets/data/posts-full.json?v=20260720-naengmyeon')
    .then(response => { if (!response.ok) throw new Error('load failed'); return response.json(); })
    .then(posts => {
      const post = posts.find(item => item.language === lang && equivalentSlug(item.slug, requestedSlug));
      if (!post) { error(); return; }
      if (requestedSlug !== slug) history.replaceState(null, '', `${location.pathname}?slug=${encodeURIComponent(post.slug)}`);
      const title = decode(post.title);
      const back = lang === 'ko' ? '모든 레시피로 돌아가기' : 'Back to all recipes';
      const category = lang === 'ko' ? '한식 레시피' : 'KOREAN RECIPE';
      document.title = `${title} — KFOOD Journal`;
      root.innerHTML = `<article class="article-shell"><a class="article-back" href="${lang === 'ko' ? '/ko' : ''}/recipes/">← ${back}</a><header class="article-header"><div><p class="article-kicker">${category}</p><h1 class="article-title">${title}</h1><p class="article-meta">${post.date} · KFOOD JOURNAL</p></div>${post.image ? `<img class="article-lead-image" src="${post.image}" alt="${title}" decoding="async">` : ''}</header><div class="article-body">${cleanContent(post.content)}</div></article>`;
      localizeArticleLinks(posts);
    })
    .catch(error);
})();
