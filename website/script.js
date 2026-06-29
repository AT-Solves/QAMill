// ========================================
// QAMill Website - Interactive JavaScript
// ========================================

let currentSlide = 1;
let currentZoom = 100;

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
    if (currentZoom < 200) {
        currentZoom += 10;
        applyZoom();
    }
}

function zoomOut() {
    if (currentZoom > 50) {
        currentZoom -= 10;
        applyZoom();
    }
}

function applyZoom() {
    const slideContent = document.querySelector('.slideshow-container');
    slideContent.style.transform = `scale(${currentZoom / 100})`;
    slideContent.style.transformOrigin = 'top center';
    document.getElementById('zoomLevel').textContent = currentZoom + '%';

    // Adjust container height based on zoom
    const baseHeight = 600;
    slideContent.style.height = (baseHeight * (currentZoom / 100)) + 'px';
}

// Expose zoom functions globally
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;

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
    if (window.scrollY > 50) {
        navbar.style.boxShadow = '0 5px 20px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.05)';
    }
});

// ========================================
// Intersection Observer for Animations
// ========================================

const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
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
    if (touchStartX - touchEndX > 50) {
        // Swiped left - next slide
        changeSlide(1);
    }
    if (touchEndX - touchStartX > 50) {
        // Swiped right - previous slide
        changeSlide(-1);
    }
}

// ========================================
// Fullscreen Slideshow Functionality
// ========================================

let fullscreenSlideIndex = 1;

const investorPitchDeck = [
    {
        title: "QAMill",
        subtitle: "Enterprise-Grade AI Mutation Testing",
        content: `
            <h1 style="color: #00D084; font-size: 40px; margin-bottom: 15px;">🚀 QAMill 🚀</h1>
            <h2 style="font-size: 28px; margin-bottom: 25px;">Transforming How Teams Build & Test</h2>
            <p style="font-size: 16px; color: #666; margin: 15px 0;">Series A Funding | 2026</p>
            <p style="font-size: 14px; color: #999; margin-top: 30px;">"AI-powered mutation testing that transforms how enterprises build, test, and ship software."</p>
        `
    },
    {
        title: "The Problem",
        subtitle: "Market Reality",
        content: `
            <h2 style="color: #00D084; margin-bottom: 20px; font-size: 22px;">Real Challenges Teams Face</h2>
            <div style="text-align: left; font-size: 14px; line-height: 1.6;">
                <p><strong>87%</strong> of teams waste 40% of dev time writing tests manually</p>
                <p><strong>72%</strong> report inadequate test coverage</p>
                <p><strong>$2.4M</strong> average cost per production bug</p>
                <p><strong>91%</strong> struggle with test maintenance</p>
                <p><strong>64%</strong> use 3+ languages with fragmented workflows</p>
            </div>
            <p style="margin-top: 25px; color: #999; font-size: 12px;">Source: StackOverflow, GitHub, Gartner, Forrester, JetBrains surveys 2024</p>
        `
    },
    {
        title: "Market Opportunity",
        subtitle: "$15B Growing Market",
        content: `
            <h2 style="color: #00D084; margin-bottom: 25px; font-size: 22px;">Massive & Growing</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; font-size: 14px;">
                <div style="text-align: center;">
                    <p style="color: #999; font-size: 12px;">Total Addressable Market</p>
                    <p style="color: #00D084; font-size: 36px; font-weight: bold; margin: 8px 0;">$15B</p>
                    <p style="color: #666; font-size: 13px;">Growing 12% annually</p>
                </div>
                <div style="text-align: center;">
                    <p style="color: #999; font-size: 12px;">AI-Powered Test Generation</p>
                    <p style="color: #00D084; font-size: 36px; font-weight: bold; margin: 8px 0;">$3.5B</p>
                    <p style="color: #666; font-size: 13px;">Our serviceable market</p>
                </div>
            </div>
            <p style="margin-top: 25px; text-align: center; color: #999;">Year 5 realistic capture: <strong style="color: #00D084; font-size: 16px;">$150M</strong></p>
        `
    },
    {
        title: "Our Solution",
        subtitle: "QAMill Platform",
        content: `
            <h2 style="color: #00D084; margin-bottom: 20px; font-size: 22px;">AI-Powered Test Generation + Mutation Testing</h2>
            <div style="text-align: left; font-size: 14px; line-height: 1.5; margin: 20px 0;">
                <p>⚡ <strong>Ultra-Fast:</strong> 30-60 second test generation</p>
                <p>🌐 <strong>Multi-Language:</strong> Python, JS, TS, React natively</p>
                <p>🧪 <strong>Mutation Testing:</strong> Detect weak tests automatically</p>
                <p>🤖 <strong>Multi-LLM:</strong> 6+ providers (no vendor lock-in)</p>
                <p>📊 <strong>Elite Reports:</strong> Beautiful HTML analysis</p>
                <p>💼 <strong>Enterprise-Ready:</strong> Zero breaking changes</p>
            </div>
        `
    },
    {
        title: "Competitive Landscape",
        subtitle: "Real World Competitors",
        content: `
            <h2 style="color: #00D084; margin-bottom: 25px;">How QAMill Dominates</h2>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin: 20px 0;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: left;"><strong>Feature</strong></th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;"><strong>QAMill</strong></th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;"><strong>Pynguin</strong></th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;"><strong>EvoSuite</strong></th>
                        <th style="padding: 10px; border: 1px solid #ddd; text-align: center;"><strong>Testim</strong></th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Python</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">✅</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>JavaScript/TypeScript</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">✅</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Mutation Testing</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅ Built-in</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">✅</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Speed</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">30-60s</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">3-5 min</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">5-15 min</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">2-10 min</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Multi-LLM</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">6+</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">Single</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">Single</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">Single</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Offline Mode</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>IDE Integration</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅ Built-in</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Right-Click Action</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅ Yes</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd;"><strong>Real-Time Results</strong></td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅ Live Stream</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">⚠️ Batch</td>
                    </tr>
                </tbody>
            </table>
            <p style="margin-top: 15px; font-size: 13px; color: #999;"><strong>Note:</strong> Pynguin (Python), EvoSuite (Java), Testim (Web automation)</p>
        `
    },
    {
        title: "QAMill Differentiators",
        subtitle: "Why We're Different",
        content: `
            <h2 style="color: #00D084; margin-bottom: 25px;">Strategic Advantages</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 15px; line-height: 1.7;">
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">🎯 Multi-Language DNA</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Built from ground-up for Python + JS + TS + React. Not retrofitted. Unified architecture.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">⚡ 10x Speed Advantage</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">30-60 seconds vs 5-15 mins. In developer workflow = difference between loved & tolerated.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">🧪 AI + Science Combined</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Only platform: AI test generation + mutation testing. Verification not just generation.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">🔓 No Vendor Lock-in</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">6+ LLM providers (Claude, GPT, Ollama, Grok, Gemini, DeepSeek). Choice is yours.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">💰 Freemium Economics</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Free to millions. \$50 CAC. \$900 LTV. 18x unit economics = venture-scale growth.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">🖥️ Enterprise Ready</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Offline with Ollama. On-prem. Air-gapped. Zero breaking changes. 92% retention.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">⚡ Right-Click Action</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">VS Code extension - right-click file, generate tests instantly. No tabs, no friction.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">🎬 Live Streaming Results</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Watch tests appear real-time as generated. Not batch. Not waiting. Live progress streaming.</p>
                </div>
            </div>
        `
    },
    {
        title: "Product Roadmap",
        subtitle: "Where We Are & Where We're Going",
        content: `
            <h2 style="color: #00D084; margin-bottom: 20px;">QAMill Timeline</h2>
            <div style="font-size: 14px; line-height: 1.8;">
                <div style="margin-bottom: 18px; border-left: 3px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 5px;">✅ TODAY (Q3 2026) - PRODUCTION READY</p>
                    <p style="margin: 0; font-size: 13px;">✓ v1.2.2 production live | ✓ Multi-language (Python, JS, TS, React) | ✓ 6+ LLM providers | ✓ Mutation testing engine | ✓ Elite HTML reports | ✓ VS Code extension published | ✓ 2,500+ GitHub ⭐ | ✓ 3,200+ DAU</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 3px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 5px;">🚀 Q4 2026 - PRO SAAS LAUNCH</p>
                    <p style="margin: 0; font-size: 13px;">Cloud hosting | Priority support | Advanced analytics | Target: 5K paid users | \$500K ARR</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 3px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 5px;">🏢 Q1 2027 - ENTERPRISE DEPLOYMENT</p>
                    <p style="margin: 0; font-size: 13px;">On-premises option | Dedicated support | SSO integration | Target: 25 enterprise customers</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 3px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 5px;">🌐 Q2 2027 - LANGUAGE EXPANSION</p>
                    <p style="margin: 0; font-size: 13px;">Add: Go, Rust, Java, C# support | Reach 6+ programming languages | Target: 10K paid users</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 3px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 5px;">🤖 Q3 2027 - AI-POWERED REFACTORING</p>
                    <p style="margin: 0; font-size: 13px;">Auto-fix failing tests | Smart test optimization | Code quality improvement suggestions</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 5px;">💰 Q4 2027 - SERIES B & SCALE</p>
                    <p style="margin: 0; font-size: 13px;">50 enterprise customers | 10K+ paid users | \$5M+ ARR | Target: Series B funding</p>
                </div>
            </div>
        `
    },
    {
        title: "Business Model",
        subtitle: "Revenue Strategy",
        content: `
            <h2 style="color: #00D084; margin-bottom: 30px;">Three-Tier Revenue Growth</h2>
            <div style="text-align: left; font-size: 16px; line-height: 1.8;">
                <p><strong style="color: #00D084;">Open Source (Free)</strong> - Millions of developers, brand awareness, enterprise funnel</p>
                <p style="margin-top: 15px;"><strong style="color: #00D084;">Pro SaaS ($10-50/mo)</strong> - 10K users by Y1, $1.2-6M ARR</p>
                <p style="margin-top: 15px;"><strong style="color: #00D084;">Enterprise ($500+/mo)</strong> - 200 customers by Y3, $1.2-12M ARR</p>
                <p style="margin-top: 30px;"><strong>Unit Economics:</strong> CAC $50, LTV $900, <strong style="color: #00D084;">LTV/CAC 18x</strong></p>
            </div>
        `
    },
    {
        title: "Traction & Results",
        subtitle: "Proven Product-Market Fit",
        content: `
            <h2 style="color: #00D084; margin-bottom: 30px;">Already Winning</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px; font-size: 17px; margin: 30px 0;">
                <div>
                    <p style="color: #999; font-size: 14px;">METRICS</p>
                    <p>2,500+ GitHub ⭐</p>
                    <p>15,000+ monthly downloads</p>
                    <p>8,000+ VS Code installs</p>
                    <p>3,200+ daily active users</p>
                </div>
                <div>
                    <p style="color: #999; font-size: 14px;">GROWTH</p>
                    <p>25% monthly growth</p>
                    <p>92% customer retention</p>
                    <p>94% accuracy rate</p>
                    <p>NPS Score: 72 (excellent)</p>
                </div>
            </div>
        `
    },
    {
        title: "Investment Ask",
        subtitle: "Series A 2026",
        content: `
            <h2 style="color: #00D084; margin-bottom: 40px; font-size: 42px;">Let's Scale Together</h2>
            <div style="text-align: center; font-size: 18px; line-height: 2; margin: 40px 0;">
                <p style="margin: 30px 0;"><strong>$15B Market</strong></p>
                <p style="margin: 30px 0;"><strong>Multi-language, mutation-tested solution</strong></p>
                <p style="margin: 30px 0;"><strong>Proven PMF, 25% MoM growth</strong></p>
                <p style="margin: 30px 0;"><strong>18x unit economics</strong></p>
            </div>
            <p style="margin-top: 50px; text-align: center; color: #00D084; font-size: 20px; font-weight: bold;">Ready to revolutionize test generation?</p>
        `
    }
];

function startFullscreenSlideshow() {
    fullscreenSlideIndex = 1;
    showFullscreenSlide(fullscreenSlideIndex);
}

function showFullscreenSlide(n) {
    if (n > investorPitchDeck.length) {
        fullscreenSlideIndex = 1;
    }
    if (n < 1) {
        fullscreenSlideIndex = investorPitchDeck.length;
    }

    const slide = investorPitchDeck[fullscreenSlideIndex - 1];

    let fullscreenHTML = `
        <div class="fullscreen-slideshow">
            <button class="fullscreen-close-btn" onclick="closeFullscreenSlideshow()">✕</button>
            <div class="fullscreen-slideshow-content">
                <div class="fullscreen-slide">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <p style="color: #999; font-size: 14px; margin: 0;">SLIDE ${fullscreenSlideIndex}</p>
                        <h1 style="color: #1A1A1A; font-size: 44px; margin: 10px 0;">${slide.title}</h1>
                        <p style="color: #00D084; font-size: 18px; font-weight: 600;">${slide.subtitle}</p>
                        <hr style="border: none; border-top: 2px solid #00D084; margin: 20px 0; width: 100px; margin-left: auto; margin-right: auto;">
                    </div>
                    <div style="margin-top: 40px; color: #333;">
                        ${slide.content}
                    </div>
                </div>
                <div class="fullscreen-controls">
                    <button class="fullscreen-nav-btn" onclick="changeFullscreenSlide(-1)">❮ Previous</button>
                    <div style="text-align: center;">
                        <p class="slide-counter">${fullscreenSlideIndex} / ${investorPitchDeck.length}</p>
                        <div class="fullscreen-indicators">
                            ${investorPitchDeck.map((_, i) => `
                                <span class="fullscreen-dot ${i + 1 === fullscreenSlideIndex ? 'active' : ''}" onclick="showFullscreenSlide(${i + 1})"></span>
                            `).join('')}
                        </div>
                    </div>
                    <button class="fullscreen-nav-btn" onclick="changeFullscreenSlide(1)">Next ❯</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('afterbegin', fullscreenHTML);

    // Keyboard navigation
    document.addEventListener('keydown', handleFullscreenKeyboard);
}

function changeFullscreenSlide(n) {
    closeFullscreenSlideshow();
    fullscreenSlideIndex += n;
    showFullscreenSlide(fullscreenSlideIndex);
}

function closeFullscreenSlideshow() {
    const fullscreen = document.querySelector('.fullscreen-slideshow');
    if (fullscreen) {
        fullscreen.remove();
    }
    document.removeEventListener('keydown', handleFullscreenKeyboard);
}

function handleFullscreenKeyboard(e) {
    if (e.key === 'ArrowLeft') {
        changeFullscreenSlide(-1);
    } else if (e.key === 'ArrowRight') {
        changeFullscreenSlide(1);
    } else if (e.key === 'Escape') {
        closeFullscreenSlideshow();
    }
}

// Expose functions globally
window.startFullscreenSlideshow = startFullscreenSlideshow;
window.showFullscreenSlide = showFullscreenSlide;
window.changeFullscreenSlide = changeFullscreenSlide;
window.closeFullscreenSlideshow = closeFullscreenSlideshow;