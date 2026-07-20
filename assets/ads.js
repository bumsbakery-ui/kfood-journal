(() => {
  const publisherId = 'ca-pub-5699330365644775';
  const contentSlotId = '1340029023';
  const isLiveSite = location.hostname === 'kfood.bumkok.com';
  const ko = document.documentElement.lang === 'ko';

  const createZone = (placement) => {
    const zone = document.createElement('aside');
    zone.className = 'ad-zone';
    zone.dataset.adPlacement = placement;
    zone.setAttribute('aria-label', ko ? '광고' : 'Advertisement');
    zone.innerHTML = `<span class="ad-zone-label">${ko ? '광고' : 'ADVERTISEMENT'}</span><ins class="adsbygoogle" style="display:block" data-ad-client="${publisherId}" data-ad-slot="${contentSlotId}" data-ad-format="auto" data-full-width-responsive="true"></ins>`;
    return zone;
  };

  const watchStatus = (zone) => {
    const ad = zone.querySelector('.adsbygoogle');
    const sync = () => {
      const status = ad.dataset.adStatus;
      zone.classList.toggle('is-filled', status === 'filled');
      zone.classList.toggle('is-unfilled', status === 'unfilled');
    };
    new MutationObserver(sync).observe(ad, { attributes: true, attributeFilter: ['data-ad-status'] });
    sync();
  };

  const activate = (zone) => {
    if (!zone || zone.dataset.adInitialized) return;
    zone.dataset.adInitialized = 'true';
    watchStatus(zone);
    if (!isLiveSite) {
      zone.classList.add('is-preview');
      return;
    }
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch {}
  };

  const mountAfter = (target, placement) => {
    if (!target || document.querySelector(`[data-ad-placement="${placement}"]`)) return;
    const zone = createZone(placement);
    target.insertAdjacentElement('afterend', zone);
    activate(zone);
  };

  const mountBefore = (target, placement) => {
    if (!target || document.querySelector(`[data-ad-placement="${placement}"]`)) return;
    const zone = createZone(placement);
    target.insertAdjacentElement('beforebegin', zone);
    activate(zone);
  };

  const mountRecipeArchive = () => {
    const list = document.querySelector('[data-recipe-list]');
    if (!list || list.querySelector('[data-ad-placement="recipe-archive"]')) return;
    const rows = [...list.querySelectorAll('.recipe-row')];
    if (rows.length < 8) return;
    const zone = createZone('recipe-archive');
    zone.classList.add('ad-zone-in-list');
    rows[7].insertAdjacentElement('afterend', zone);
    activate(zone);
  };

  const mountRecipeArticle = () => {
    const body = document.querySelector('.article-body');
    if (!body || body.querySelector('[data-ad-placement="recipe-article"]')) return;
    const headings = [...body.querySelectorAll('h2')];
    const anchor = headings[Math.max(1, Math.floor(headings.length / 2))] || body.children[Math.min(5, body.children.length - 1)];
    if (!anchor) return;
    const zone = createZone('recipe-article');
    anchor.insertAdjacentElement('beforebegin', zone);
    activate(zone);
  };

  if (isLiveSite) {
    const loader = document.createElement('script');
    loader.async = true;
    loader.crossOrigin = 'anonymous';
    loader.src = `https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${publisherId}`;
    document.head.appendChild(loader);
  }

  if (document.querySelector('.featured')) mountAfter(document.querySelector('.featured'), 'home-featured');
  if (document.body.classList.contains('guide-page')) mountBefore(document.querySelector('#meal'), 'food-guide');
  if (document.querySelector('.topic-grid') && !document.body.classList.contains('guide-page')) mountAfter(document.querySelector('.topic-grid'), 'stories');

  const dynamicRoot = document.querySelector('[data-recipe-list], [data-recipe-detail]');
  if (dynamicRoot) {
    let queued = false;
    const refresh = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        mountRecipeArchive();
        mountRecipeArticle();
      });
    };
    new MutationObserver(refresh).observe(dynamicRoot, { childList: true, subtree: true });
    refresh();
  }
})();
