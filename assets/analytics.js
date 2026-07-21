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

  const loader = document.createElement('script');
  loader.async = true;
  loader.src = `https://www.googletagmanager.com/gtag/js?id=${measurementId}`;
  document.head.appendChild(loader);
})();
