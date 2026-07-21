const menuButton = document.querySelector('.menu-button');
const nav = document.querySelector('.primary-nav');
const analytics = document.createElement('script');

analytics.src = '/assets/analytics.js';
document.head.appendChild(analytics);

menuButton?.addEventListener('click', () => {
  const open = nav.classList.toggle('is-open');
  menuButton.setAttribute('aria-expanded', String(open));
});
