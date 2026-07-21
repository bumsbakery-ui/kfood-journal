(() => {
  const endpoint = 'https://docs.google.com/forms/d/e/1FAIpQLSciJk---ArkrmLOsNzIg1dlCpmLkax4pRRe1sdsVMinycCPLA/formResponse';
  const fields = {
    type: 'entry.2109916404',
    language: 'entry.670130749',
    email: 'entry.2022962342',
    subject: 'entry.555598945',
    page: 'entry.882352205',
    name: 'entry.124509792',
    message: 'entry.1171844880'
  };

  const copy = {
    en: {
      sending: 'Sending…',
      contactSuccess: 'Thank you. Your message has been sent.',
      newsletterSuccess: 'You’re subscribed. Welcome to the KFOOD table.',
      error: 'We could not send this right now. Please try again.'
    },
    ko: {
      sending: '전송 중…',
      contactSuccess: '감사합니다. 문의가 정상적으로 접수되었습니다.',
      newsletterSuccess: '구독 신청이 완료되었습니다. KFOOD의 소식을 전해드릴게요.',
      error: '지금은 전송할 수 없습니다. 잠시 후 다시 시도해 주세요.'
    }
  };

  document.querySelectorAll('[data-kfood-form]').forEach((form) => {
    const lang = document.documentElement.lang === 'ko' ? 'ko' : 'en';
    const type = form.dataset.kfoodForm === 'contact' ? 'contact' : 'newsletter';
    const startedAt = Date.now();
    const button = form.querySelector('button[type="submit"]');
    const originalButton = button?.innerHTML || '';
    const status = form.querySelector('[data-form-status]');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;

      if (form.elements.website?.value || Date.now() - startedAt < 800) {
        if (status) status.textContent = type === 'contact' ? copy[lang].contactSuccess : copy[lang].newsletterSuccess;
        form.reset();
        return;
      }

      button.disabled = true;
      button.textContent = copy[lang].sending;
      if (status) {
        status.className = 'form-status';
        status.textContent = '';
      }

      const payload = new URLSearchParams();
      payload.set(fields.type, type);
      payload.set(fields.language, lang);
      payload.set(fields.email, form.elements.email?.value.trim() || '');
      payload.set(fields.subject, form.elements.subject?.value.trim() || (type === 'newsletter' ? 'Newsletter subscription' : ''));
      payload.set(fields.page, location.href);
      payload.set(fields.name, form.elements.name?.value.trim() || '');
      payload.set(fields.message, form.elements.message?.value.trim() || 'Newsletter subscription');

      try {
        await fetch(endpoint, {
          method: 'POST',
          mode: 'no-cors',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: payload.toString()
        });
        form.reset();
        if (status) {
          status.classList.add('is-success');
          status.textContent = type === 'contact' ? copy[lang].contactSuccess : copy[lang].newsletterSuccess;
        }
        if (typeof window.gtag === 'function') {
          window.gtag('event', type === 'contact' ? 'generate_lead' : 'sign_up', { method: 'KFOOD form' });
        }
      } catch {
        if (status) {
          status.classList.add('is-error');
          status.textContent = copy[lang].error;
        }
      } finally {
        button.disabled = false;
        button.innerHTML = originalButton;
      }
    });
  });
})();
