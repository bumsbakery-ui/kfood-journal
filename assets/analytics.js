(() => {
  if (window.__kfoodAnalyticsLoaded) return;
  window.__kfoodAnalyticsLoaded = true;

  const measurementId = 'G-MCDFMYRG0S';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', measurementId, {
    page_location: location.href,
    page_title: document.title
  });

  const send = (name, parameters = {}) => {
    window.gtag('event', name, {
      page_path: location.pathname,
      page_language: document.documentElement.lang || 'en',
      ...parameters
    });
  };

  let hasInteraction = false;
  let hasHalfScroll = false;
  let engagedSent = false;
  const markInteraction = () => { hasInteraction = true; };
  const maybeSendEngagedReader = () => {
    if (engagedSent || !hasInteraction || !hasHalfScroll || document.visibilityState !== 'visible') return;
    engagedSent = true;
    send('engaged_reader', { engagement_seconds: 20, scroll_depth: 50 });
  };

  ['pointerdown', 'keydown', 'touchstart'].forEach((eventName) => {
    window.addEventListener(eventName, markInteraction, { once: true, passive: true });
  });

  window.addEventListener('scroll', () => {
    const scrollable = document.documentElement.scrollHeight - innerHeight;
    if (scrollable > 0 && scrollY / scrollable >= 0.5) {
      hasHalfScroll = true;
      maybeSendEngagedReader();
    }
  }, { passive: true });

  window.setTimeout(maybeSendEngagedReader, 20000);

  document.addEventListener('click', (event) => {
    if (!(event.target instanceof Element)) return;
    const link = event.target.closest('a[href]');
    if (!link) return;
    const destination = new URL(link.href, location.href);
    if (link.classList.contains('language-link')) {
      send('language_switch', { destination_language: destination.pathname.startsWith('/ko/') ? 'ko' : 'en' });
    }
    if (destination.origin !== location.origin) {
      send('outbound_click', { destination_host: destination.hostname });
    }
  });

  const loader = document.createElement('script');
  loader.async = true;
  loader.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
  document.head.appendChild(loader);
})();
