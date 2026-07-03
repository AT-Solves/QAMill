// ========================================
// QAMill Website - Interactive JavaScript
// ========================================

import CONFIG from './config.js';

let currentSlide = 1;
let currentZoom = CONFIG.UI.ZOOM.INITIAL;

// ========================================
// Slideshow Functions
// ========================================

function showSlide(n) {
    const slides = document.querySelectorAll('.slide');
    const dots = document.querySelectorAll('.dot');

    if (n > slides.length) {
        currentSlide = 1;
    }
    if (n < 1) {
        currentSlide = slides.length;
    }

    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));

    slides[currentSlide - 1].classList.add('active');
    dots[currentSlide - 1].classList.add('active');
}

function changeSlide(n) {
    currentSlide += n;
    showSlide(currentSlide);
}

function setCurrentSlide(n) {
    currentSlide = n;
    showSlide(currentSlide);
}

// Alias for HTML onclick handlers
window.currentSlide = setCurrentSlide;

// ========================================
// Zoom Functions
// ========================================

function zoomIn() {
    if (currentZoom < CONFIG.UI.ZOOM.MAX) {
        currentZoom += CONFIG.UI.ZOOM.INCREMENT;
        applyZoom();
    }
}

function zoomOut() {
    if (currentZoom > CONFIG.UI.ZOOM.MIN) {
        currentZoom -= CONFIG.UI.ZOOM.INCREMENT;
        applyZoom();
    }
}

function applyZoom() {
    const slideContent = document.querySelector('.slideshow-container');
    slideContent.style.transform = `scale(${currentZoom / 100})`;
    slideContent.style.transformOrigin = 'top center';
    document.getElementById('zoomLevel').textContent = currentZoom + '%';

    const baseHeight = CONFIG.UI.SLIDE.BASE_HEIGHT;
    slideContent.style.height = (baseHeight * (currentZoom / 100)) + 'px';
}

// Expose zoom functions globally
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;

// ========================================
// Navigation Functions
// ========================================

function openMarketplace() {
    window.open(CONFIG.LINKS.MARKETPLACE, '_blank');
}

window.openMarketplace = openMarketplace;

// ========================================
// Keyboard Navigation
// ========================================

document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
        changeSlide(-1);
    } else if (e.key === 'ArrowRight') {
        changeSlide(1);
    }
});

// ========================================
// Smooth Scroll for Navigation Links
// ========================================

document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    });
});

// ========================================
// Navbar Background on Scroll
// ========================================

window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > CONFIG.UI.SCROLL.NAVBAR_SHADOW_THRESHOLD) {
        navbar.style.boxShadow = '0 5px 20px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.05)';
    }
});

// ========================================
// Intersection Observer for Animations
// ========================================

const observerOptions = {
    threshold: CONFIG.UI.OBSERVER.THRESHOLD,
    rootMargin: CONFIG.UI.OBSERVER.ROOT_MARGIN
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe all cards for animation
document.querySelectorAll('.intro-card, .problem-card, .contact-card, .deployment-option').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(card);
});

// ========================================
// Initialize
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize slideshow
    showSlide(currentSlide);

    // Initialize zoom
    applyZoom();

    // Add active class to current nav link based on scroll position
    window.addEventListener('scroll', () => {
        let current = '';
        const sections = document.querySelectorAll('section');

        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (pageYOffset >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });

        document.querySelectorAll('.nav-links a').forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href').slice(1) === current) {
                link.style.color = 'var(--primary-color)';
            } else {
                link.style.color = 'var(--text-primary)';
            }
        });
    });
});

// ========================================
// Touch Support for Mobile Slideshow
// ========================================

let touchStartX = 0;
let touchEndX = 0;

const slideShowContainer = document.querySelector('.slideshow-container');
if (slideShowContainer) {
    slideShowContainer.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    });

    slideShowContainer.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    });
}

function handleSwipe() {
    if (touchStartX - touchEndX > CONFIG.UI.TOUCH.SWIPE_THRESHOLD) {
        changeSlide(1);
    }
    if (touchEndX - touchStartX > CONFIG.UI.TOUCH.SWIPE_THRESHOLD) {
        changeSlide(-1);
    }
}

// Fullscreen slideshow removed - using regular page slider instead
