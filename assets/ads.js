(() => {
  const watchStatus = (zone) => {
    const ad = zone.querySelector('.adsbygoogle');
    if (!ad) return;
    const sync = () => {
      const status = ad.dataset.adStatus;
      zone.classList.toggle('is-filled', status === 'filled');
      zone.classList.toggle('is-unfilled', status === 'unfilled');
    };
    new MutationObserver(sync).observe(ad, { attributes: true, attributeFilter: ['data-ad-status'] });
    sync();
    setTimeout(() => {
      if (!ad.dataset.adStatus) zone.classList.add('is-unfilled');
    }, 12000);
  };
  document.querySelectorAll('.ad-zone').forEach(watchStatus);
})();
