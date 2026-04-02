/* ============================================
   FixNear — JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  // ---------- Mobile Nav Toggle ----------
  const hamburger = document.querySelector('.navbar__hamburger');
  const navLinks = document.querySelector('.navbar__links');

  if (hamburger) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('open');
      navLinks.classList.toggle('open');
    });

    // Close on link click
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        hamburger.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });
  }

  // ---------- Navbar scroll effect ----------
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.classList.toggle('scrolled', window.scrollY > 30);
    });
  }

  // ---------- Scroll Reveal ----------
  const revealEls = document.querySelectorAll('.reveal');
  if (revealEls.length) {
    const revealOnScroll = () => {
      const trigger = window.innerHeight * 0.88;
      revealEls.forEach(el => {
        const top = el.getBoundingClientRect().top;
        if (top < trigger) {
          el.classList.add('active');
        }
      });
    };
    window.addEventListener('scroll', revealOnScroll);
    revealOnScroll();
  }

  // ---------- Smooth scroll for anchor links ----------
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ---------- Active nav link ----------
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.navbar__links a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === currentPage || (currentPage === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });
});

// ---------- Toast Notification ----------
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
    borderRadius: '12px',
    fontSize: '.92rem',
    fontWeight: '600',
    fontFamily: "'Inter', sans-serif",
    color: '#fff',
    background: type === 'success'
      ? 'linear-gradient(135deg, #059669, #10b981)'
      : 'linear-gradient(135deg, #dc2626, #ef4444)',
    boxShadow: '0 8px 30px rgba(0,0,0,.15)',
    zIndex: 10000,
    animation: 'fadeInUp .35s ease',
    cursor: 'pointer'
  });

  toast.addEventListener('click', () => toast.remove());
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}
