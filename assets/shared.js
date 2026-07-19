(() => {
  const lang = document.documentElement.lang === 'ko' ? 'ko' : 'en';
  const ko = lang === 'ko';
  const prefix = ko ? '/ko' : '';
  const current = location.pathname.replace(/^\/ko/, '') || '/';
  const isRecipeDetail = current.startsWith('/recipe/');
  const alternate = isRecipeDetail
    ? (ko ? '/recipes/' : '/ko/recipes/')
    : (ko ? (current === '/' ? '/' : current) : `/ko${current === '/' ? '/' : current}`);
  const labels = ko
    ? { recipes:'레시피', stories:'이야기', guide:'한식 가이드', about:'소개', contact:'문의', find:'레시피 찾기', menu:'메뉴', lang:'EN' }
    : { recipes:'Recipes', stories:'Stories', guide:'Food Guide', about:'About', contact:'Contact', find:'Find a recipe', menu:'Menu', lang:'한국어' };
  const header = document.querySelector('[data-site-header]');
  if (header) header.innerHTML = `
    <div class="announcement">Korean food, remembered and shared <span>·</span> ${ko ? '매주 새로운 레시피를 만나보세요' : 'New recipes every week'}</div>
    <header class="site-header">
      <a class="wordmark" href="${prefix}/" aria-label="KFOOD Journal home">KFOOD <em>Journal</em></a>
      <button class="menu-button" aria-expanded="false" aria-controls="primary-nav">${labels.menu}</button>
      <nav id="primary-nav" class="primary-nav" aria-label="Primary navigation">
        <a href="${prefix}/recipes/">${labels.recipes}</a><a href="${prefix}/stories/">${labels.stories}</a><a href="${prefix}/food-guide/">${labels.guide}</a><a href="${prefix}/about/">${labels.about}</a><a href="${prefix}/contact/">${labels.contact}</a>
      </nav>
      <a class="language-link" href="${alternate}" lang="${ko ? 'en' : 'ko'}">${labels.lang}</a>
      <a class="search-link" href="${prefix}/recipes/">${labels.find} <span>↗</span></a>
    </header>`;
  const footer = document.querySelector('[data-site-footer]');
  if (footer) footer.innerHTML = `<footer class="site-footer route-footer"><a class="wordmark" href="${prefix}/">KFOOD <em>Journal</em></a><p>© 2026 KFOOD Journal. Korean flavors, globally shared.</p><div><a href="${prefix}/about/">${labels.about}</a><a href="${prefix}/contact/">${labels.contact}</a></div></footer>`;
  const menuButton = document.querySelector('.menu-button');
  const nav = document.querySelector('.primary-nav');
  menuButton?.addEventListener('click', () => { const open = nav.classList.toggle('is-open'); menuButton.setAttribute('aria-expanded', String(open)); });
})();
