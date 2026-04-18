document.addEventListener('DOMContentLoaded', () => {
  /* ─── Hamburger Menu ─── */
  const hamburger = document.querySelector('.navbar__hamburger');
  const navLinks = document.querySelector('.navbar__links');

  /* Contact Modal */
  const contactModal = document.getElementById('contactModal');
  const contactModalTriggers = document.querySelectorAll('[data-contact-modal]');
  const contactModalClosers = document.querySelectorAll('[data-contact-close]');

  if (contactModal && contactModalTriggers.length) {
    const openContactModal = event => {
      event.preventDefault();
      contactModal.classList.add('is-open');
      contactModal.setAttribute('aria-hidden', 'false');
      document.body.classList.add('contact-modal-open');

      const firstField = contactModal.querySelector('input, textarea');
      if (firstField) {
        setTimeout(() => firstField.focus(), 80);
      }
    };

    const closeContactModal = () => {
      contactModal.classList.remove('is-open');
      contactModal.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('contact-modal-open');
    };

    contactModalTriggers.forEach(trigger => {
      trigger.addEventListener('click', openContactModal);
    });

    contactModalClosers.forEach(closer => {
      closer.addEventListener('click', closeContactModal);
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && contactModal.classList.contains('is-open')) {
        closeContactModal();
      }
    });
  }

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('open');
      navLinks.classList.toggle('open');
    });

    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        hamburger.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });
  }

  /* ─── Navbar Scroll State ─── */
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    const syncNavbar = () => {
      navbar.classList.toggle('scrolled', window.scrollY > 18);
    };

    window.addEventListener('scroll', syncNavbar, { passive: true });
    syncNavbar();
  }

  /* ─── Reveal on Scroll ─── */
  const revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    const revealOnScroll = () => {
      const trigger = window.innerHeight * 0.88;

      revealEls.forEach((el, i) => {
        if (el.getBoundingClientRect().top < trigger && !el.classList.contains('active')) {
          let delay = i % 3 * 80;
          const stepsParent = el.closest('.guide-preview__steps');
          if (stepsParent) {
            delay = Array.from(stepsParent.children).indexOf(el) * 130;
          }

          const faqParent = el.closest('.faq__list');
          if (faqParent) {
            delay = Array.from(faqParent.children).indexOf(el) * 95;
          }

          setTimeout(() => {
            el.classList.add('active');
          }, delay);
        }
      });
    };

    window.addEventListener('scroll', revealOnScroll, { passive: true });
    revealOnScroll();
  }

  /* ─── Smooth Anchor Scroll ─── */
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', event => {
      const href = anchor.getAttribute('href');
      const target = href ? document.querySelector(href) : null;

      if (!target) {
        return;
      }

      event.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  /* ─── Active Nav Link ─── */
  const currentPath = window.location.pathname.replace(/\/+$/, '') || '/';
  document.querySelectorAll('.navbar__links a').forEach(link => {
    const href = link.getAttribute('href');

    if (!href || href.startsWith('#')) {
      return;
    }

    const normalizedHref = new URL(href, window.location.origin).pathname.replace(/\/+$/, '') || '/';
    if (normalizedHref === currentPath) {
      link.classList.add('active');
    }
  });

  /* ─── FAQ Accordion (Smooth) ─── */
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    const trigger = item.querySelector('.faq-item__trigger');
    const content = item.querySelector('.faq-item__content');

    if (!trigger || !content) {
      return;
    }

    trigger.addEventListener('click', () => {
      const isOpen = item.classList.contains('is-active');

      // Close all others smoothly
      faqItems.forEach(otherItem => {
        if (otherItem === item) return;

        const otherTrigger = otherItem.querySelector('.faq-item__trigger');
        const otherContent = otherItem.querySelector('.faq-item__content');

        otherItem.classList.remove('is-active');

        if (otherTrigger) {
          otherTrigger.setAttribute('aria-expanded', 'false');
        }

        if (otherContent) {
          otherContent.style.maxHeight = '0';
          otherContent.style.paddingBottom = '0';
          otherContent.classList.remove('is-open');
        }
      });

      // Toggle current
      if (!isOpen) {
        item.classList.add('is-active');
        trigger.setAttribute('aria-expanded', 'true');
        content.classList.add('is-open');
        content.style.maxHeight = content.scrollHeight + 24 + 'px';
        content.style.paddingBottom = '22px';
      } else {
        item.classList.remove('is-active');
        trigger.setAttribute('aria-expanded', 'false');
        content.style.maxHeight = '0';
        content.style.paddingBottom = '0';
        // Delay removing is-open until transition completes
        setTimeout(() => {
          if (!item.classList.contains('is-active')) {
            content.classList.remove('is-open');
          }
        }, 400);
      }
    });
  });

  /* ─── Initialize default open FAQ ─── */
  const defaultOpenFaq = document.querySelector('.faq-item__content.is-open');
  if (defaultOpenFaq) {
    const parent = defaultOpenFaq.closest('.faq-item');
    const trigger = parent ? parent.querySelector('.faq-item__trigger') : null;

    if (parent) {
      parent.classList.add('is-active');
    }

    if (trigger) {
      trigger.setAttribute('aria-expanded', 'true');
    }

    // Set initial max-height for the default open item
    requestAnimationFrame(() => {
      defaultOpenFaq.style.maxHeight = defaultOpenFaq.scrollHeight + 24 + 'px';
      defaultOpenFaq.style.paddingBottom = '22px';
    });
  }
});

/* ─── Toast Notification ─── */
function showToast(message, type = 'success') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast--${type}`;
  toast.innerHTML = `
    <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
    <span>${message}</span>
  `;

  Object.assign(toast.style, {
    position: 'fixed',
    top: '24px',
    right: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '14px 24px',
    borderRadius: '14px',
    fontSize: '.9rem',
    fontWeight: '600',
    fontFamily: "'Inter', sans-serif",
    color: '#EAF2FF',
    background: type === 'success'
      ? '#2F6BFF'
      : 'linear-gradient(180deg, #c2410c 0%, #9a3412 100%)',
    boxShadow: '0 8px 24px rgba(0, 0, 0, .2)',
    zIndex: 10000,
    animation: 'fadeInUp .3s cubic-bezier(0.4, 0, 0.2, 1)',
    cursor: 'pointer'
  });

  toast.addEventListener('click', () => toast.remove());
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
