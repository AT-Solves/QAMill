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
        title: "Elevator Pitch",
        subtitle: "The Opportunity",
        content: `
            <div style="text-align: left; font-size: 12px; line-height: 1.4; overflow-y: auto; height: 100%; padding-right: 8px;">
                <h2 style="color: #00D084; margin-bottom: 8px; font-size: 18px;">QAMill</h2>
                <p style="margin-bottom: 8px;"><strong>Enterprise-Grade AI Mutation Testing Platform</strong></p>

                <p style="margin-bottom: 6px;"><strong>Problem:</strong> Development teams waste 40% of time writing tests manually, resulting in weak test suites and expensive production bugs averaging $2.4M each.</p>

                <p style="margin-bottom: 6px;"><strong>Solution:</strong> AI-powered test generation combined with mutation testing. Generate comprehensive test suites in 30-60 seconds. Verify tests actually catch bugs.</p>

                <p style="margin-bottom: 6px;"><strong>Market:</strong> $15 billion testing automation market growing 12% annually. $3.5B AI-powered test generation segment. $150M realistic 5-year capture.</p>

                <p style="margin-bottom: 6px;"><strong>Differentiation:</strong> Only platform with true multi-language support (Python, JavaScript, TypeScript, React) + mutation testing + 6+ LLM providers. 10x faster than competitors. Right-click IDE integration with real-time streaming results.</p>

                <p style="margin-bottom: 8px;"><strong>Traction:</strong> 2,500+ GitHub stars, 8,000+ VS Code extension installs, 3,200+ daily active users, 92% customer retention, 25% month-over-month growth.</p>

                <div style="background: #f9f9f9; border-left: 3px solid #00D084; padding: 15px; margin-top: 5px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 8px;">12-Month Roadmap</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Now (Q3 2026):</strong> v1.2.2 production-ready, multi-language, 6+ LLM providers, mutation testing</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Q4 2026:</strong> Pro SaaS tier launch ($10-50/mo), cloud hosting, 5K users target</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Q1 2027:</strong> Enterprise on-premises, SSO integration, 25 customers target</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Q2-Q4 2027:</strong> 4 new languages (Go, Rust, Java, C#), AI-powered test refactoring, Series B funding</p>
                </div>

                <p style="margin-top: 5px;"><strong>Business Model:</strong> 3-tier revenue: Free open-source (millions of users), Pro SaaS ($1.2-6M Y1 ARR), Enterprise ($1.2-12M Y3 ARR). Projected $20M+ ARR by Year 5.</p>

                <p style="margin-top: 15px; color: #00D084; font-weight: bold;">Ask: Series A funding to scale sales, expand language support, and capture market leadership.</p>
            </div>
        `
    },
    {
        title: "Market Problem",
        subtitle: "The Opportunity",
        content: `
            <div style="text-align: left; font-size: 12px; line-height: 1.4;">
                <h2 style="color: #00D084; margin-bottom: 6px; font-size: 18px;">Testing Remains the Bottleneck</h2>

                <div style="margin-bottom: 8px;">
                    <p style="margin: 12px 0;"><strong>87% of teams</strong> spend 40% of development time writing tests manually</p>
                    <p style="margin: 12px 0;"><strong>72% report</strong> inadequate test coverage and missed edge cases</p>
                    <p style="margin: 12px 0;"><strong>91% struggle</strong> with test maintenance when code changes</p>
                    <p style="margin: 12px 0;"><strong>64% maintain</strong> 3+ languages with separate testing workflows</p>
                    <p style="margin: 12px 0;"><strong>Average cost:</strong> $2.4M per production bug that escapes testing</p>
                </div>

                <div style="background: #f9f9f9; border-left: 3px solid #00D084; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Impact:</strong> Teams lose 2+ days of productivity per developer per week. Code quality lags. Bugs reach production. Development velocity stalls.</p>
                </div>

                <p style="margin-top: 5px; color: #666; font-size: 13px;">Data sources: StackOverflow Developer Survey 2024, GitHub State of Octoverse 2024, Gartner Report 2024, Forrester Research 2024, JetBrains Ecosystem Survey 2024</p>
            </div>
        `
    },
    {
        title: "Market Size & Opportunity",
        subtitle: "$15 Billion Testing Automation Market",
        content: `
            <div style="text-align: center; font-size: 15px;">
                <h2 style="color: #00D084; margin-bottom: 30px; font-size: 18px;">Massive Addressable Market</h2>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-bottom: 30px;">
                    <div style="text-align: left; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
                        <p style="color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 6px;">TAM - Total Addressable Market</p>
                        <p style="color: #00D084; font-size: 32px; font-weight: bold; margin: 0;">$15B</p>
                        <p style="color: #666; font-size: 13px; margin-top: 8px;">Global testing automation market growing 12% annually</p>
                    </div>
                    <div style="text-align: left; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
                        <p style="color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 6px;">SAM - Serviceable Addressable Market</p>
                        <p style="color: #00D084; font-size: 32px; font-weight: bold; margin: 0;">$3.5B</p>
                        <p style="color: #666; font-size: 13px; margin-top: 8px;">AI-powered test generation segment (our focus)</p>
                    </div>
                </div>

                <div style="background: #f0f9f6; border-left: 4px solid #00D084; padding: 20px; margin: 20px 0; text-align: left;">
                    <p style="color: #00D084; font-weight: bold; font-size: 16px; margin-bottom: 6px;">SOM - Serviceable Obtainable Market (Year 5)</p>
                    <p style="margin: 0; font-size: 16px;"><strong style="color: #00D084;">$150M</strong> - Conservative, realistic capture target</p>
                </div>

                <div style="text-align: left; margin-top: 5px; font-size: 14px;">
                    <p style="color: #666;"><strong>Growth Drivers:</strong> 87% of teams want AI tools, 50% use 3+ languages, 15% annual increase in quality investment, shift-left testing adoption</p>
                </div>
            </div>
        `
    },
    {
        title: "QAMill Solution",
        subtitle: "AI-Powered Test Generation with Mutation Testing",
        content: `
            <div style="text-align: left; font-size: 15px; line-height: 1.7;">
                <h2 style="color: #00D084; margin-bottom: 8px; font-size: 18px;">How QAMill Works</h2>

                <div style="margin-bottom: 6px;">
                    <p style="margin: 12px 0;"><strong>Ultra-Fast Generation:</strong> Generates comprehensive test suites in 30-60 seconds. Real-time streaming shows progress as tests are created.</p>

                    <p style="margin: 12px 0;"><strong>Multi-Language Support:</strong> Native support for Python, JavaScript, TypeScript, and React. Single platform for entire tech stack.</p>

                    <p style="margin: 12px 0;"><strong>Mutation Testing:</strong> Automatically detects weak tests and generates healing tests. Verifies tests actually catch bugs.</p>

                    <p style="margin: 12px 0;"><strong>LLM Flexibility:</strong> Choose from 6+ AI providers (Claude, GPT-4, Ollama, Grok, Gemini, DeepSeek, Mistral). No vendor lock-in.</p>

                    <p style="margin: 12px 0;"><strong>IDE Integration:</strong> VS Code extension with right-click action. Generate tests directly from your editor without context switching.</p>

                    <p style="margin: 12px 0;"><strong>Professional Reports:</strong> Elite HTML reports with mutation analysis, coverage metrics, and actionable insights.</p>
                </div>

                <div style="background: #f0f9f6; border-left: 4px solid #00D084; padding: 15px; margin-top: 5px;">
                    <p style="margin: 0;"><strong>Enterprise Grade:</strong> On-premises deployment, offline capability, 100% backward compatibility, 92% customer retention.</p>
                </div>
            </div>
        `
    },
    {
        title: "Competitive Landscape",
        subtitle: "Real World Competitors",
        content: `
            <h2 style="color: #00D084; margin-bottom: 6px;">How QAMill Dominates</h2>
            <table style="width: 100%; border-collapse: collapse; font-size: 11px; margin: 15px 0; line-height: 1.3;">
                <thead>
                    <tr style="background: #f5f5f5;">
                        <th style="padding: 6px; border: 1px solid #ddd; text-align: left; font-size: 11px;"><strong>Feature</strong></th>
                        <th style="padding: 6px; border: 1px solid #ddd; text-align: center; font-size: 11px;"><strong>QAMill</strong></th>
                        <th style="padding: 6px; border: 1px solid #ddd; text-align: center; font-size: 11px;"><strong>Pynguin</strong></th>
                        <th style="padding: 6px; border: 1px solid #ddd; text-align: center; font-size: 11px;"><strong>EvoSuite</strong></th>
                        <th style="padding: 6px; border: 1px solid #ddd; text-align: center; font-size: 11px;"><strong>Testim</strong></th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>Python</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>JS/TS</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">✅</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>Mutation</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>Speed</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">30-60s</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">3-5m</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">5-15m</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">2-10m</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>Multi-LLM</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">6+</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">1</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">1</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">1</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>Offline</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr>
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>IDE</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                    </tr>
                    <tr style="background: #fafafa;">
                        <td style="padding: 5px; border: 1px solid #ddd; font-size: 11px;"><strong>Real-time</strong></td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center; color: #00D084;">✅</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">❌</td>
                        <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">⚠️</td>
                    </tr>
                </tbody>
            </table>
            <p style="margin-top: 8px; font-size: 11px; color: #999;"><strong>Note:</strong> Pynguin (Python), EvoSuite (Java), Testim (Web automation)</p>
        `
    },
    {
        title: "QAMill Differentiators",
        subtitle: "Why We're Different",
        content: `
            <h2 style="color: #00D084; margin-bottom: 6px;">Strategic Advantages</h2>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 15px; line-height: 1.7;">
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">Multi-Language DNA</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Built from ground-up for Python + JS + TS + React. Not retrofitted. Unified architecture.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">10x Speed Advantage</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">30-60 seconds vs 5-15 mins. In developer workflow = difference between loved & tolerated.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">AI + Science Combined</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Only platform: AI test generation + mutation testing. Verification not just generation.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">No Vendor Lock-in</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">6+ LLM providers (Claude, GPT, Ollama, Grok, Gemini, DeepSeek). Choice is yours.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">Freemium Economics</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Free to millions. \$50 CAC. \$900 LTV. 18x unit economics = venture-scale growth.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">Enterprise Ready</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Offline with Ollama. On-prem. Air-gapped. Zero breaking changes. 92% retention.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">Right-Click Extension</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">VS Code integration with right-click action on files. Generate tests instantly without leaving your editor or using a web interface.</p>
                </div>
                <div style="border-left: 3px solid #00D084; padding-left: 15px;">
                    <p><strong style="color: #00D084;">Real-Time Streaming Results</strong></p>
                    <p style="font-size: 13px; margin-top: 8px;">Watch tests appear as they're generated in real-time. Live progress streaming with instant feedback, not batch processing.</p>
                </div>
            </div>
        `
    },
    {
        title: "Product Roadmap",
        subtitle: "Where We Are & Where We're Going",
        content: `
            <h2 style="color: #00D084; margin-bottom: 8px;">QAMill Timeline</h2>
            <div style="font-size: 14px; line-height: 1.8;">
                <div style="margin-bottom: 18px; border-left: 4px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">TODAY (Q3 2026) - PRODUCTION READY</p>
                    <p style="margin: 0; font-size: 13px; color: #666;">v1.2.2 production live, multi-language support (Python, JavaScript, TypeScript, React), 6+ LLM providers, mutation testing engine, elite HTML reports, VS Code extension published, 2,500+ GitHub stars, 3,200+ daily active users</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 4px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Q4 2026 - PRO SAAS LAUNCH</p>
                    <p style="margin: 0; font-size: 13px; color: #666;">Cloud hosting, priority support, advanced analytics, user dashboard. Target: 5,000 paid users. Revenue target: $500K ARR</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 4px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Q1 2027 - ENTERPRISE DEPLOYMENT</p>
                    <p style="margin: 0; font-size: 13px; color: #666;">On-premises deployment option, dedicated enterprise support, SSO integration, compliance tooling. Target: 25 enterprise customers</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 4px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Q2 2027 - LANGUAGE EXPANSION</p>
                    <p style="margin: 0; font-size: 13px; color: #666;">Add Go, Rust, Java, and C# support. Expand to 6+ programming languages. Target: 10K paid users across all tiers</p>
                </div>
                <div style="margin-bottom: 18px; border-left: 4px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Q3 2027 - AI-POWERED REFACTORING</p>
                    <p style="margin: 0; font-size: 13px; color: #666;">Auto-fix failing tests, smart test optimization, code quality improvement suggestions, advanced mutation analysis</p>
                </div>
                <div style="border-left: 4px solid #00D084; padding-left: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Q4 2027 - SERIES B & MARKET SCALE</p>
                    <p style="margin: 0; font-size: 13px; color: #666;">50+ enterprise customers, 10,000+ paid users, $5M+ annual recurring revenue, launch Series B funding round, expand sales and engineering teams</p>
                </div>
            </div>
        `
    },
    {
        title: "Business Model",
        subtitle: "Three-Tier Revenue Strategy",
        content: `
            <div style="text-align: left; font-size: 14px; line-height: 1.7;">
                <h2 style="color: #00D084; margin-bottom: 8px; font-size: 18px;">Scalable Revenue Growth</h2>

                <div style="margin-bottom: 6px;">
                    <div style="border: 1px solid #e0e0e0; padding: 14px; margin-bottom: 8px; border-radius: 6px;">
                        <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Open Source (Free)</p>
                        <p style="margin: 0; color: #666; font-size: 13px;">Community growth engine. Millions of developers. Brand awareness and enterprise pipeline.</p>
                    </div>

                    <div style="border: 1px solid #e0e0e0; padding: 14px; margin-bottom: 8px; border-radius: 6px;">
                        <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Pro SaaS ($10-50/month)</p>
                        <p style="margin: 0; color: #666; font-size: 13px;">Cloud hosting, priority support, analytics. Target: 10K users by Year 1. Projected $1.2-6M annual recurring revenue.</p>
                    </div>

                    <div style="border: 1px solid #e0e0e0; padding: 14px; border-radius: 6px;">
                        <p style="color: #00D084; font-weight: bold; margin-bottom: 6px;">Enterprise ($500-5,000/month)</p>
                        <p style="margin: 0; color: #666; font-size: 13px;">On-prem, dedicated support, SSO. Target: 50-200 customers by Year 3. Projected $1.2-12M annual recurring revenue.</p>
                    </div>
                </div>

                <div style="background: #f0f9f6; border-left: 4px solid #00D084; padding: 12px; margin-top: 18px;">
                    <p style="margin-bottom: 6px; color: #00D084; font-weight: bold; font-size: 13px;">Unit Economics (Pro Tier)</p>
                    <p style="margin: 0; font-size: 13px;">CAC: $50 | LTV: $900 | LTV/CAC: 18x</p>
                </div>

                <p style="margin-top: 15px; font-size: 13px;"><strong>Year 5 Target:</strong> $20M+ annual recurring revenue</p>
            </div>
        `
    },
    {
        title: "Traction & Product-Market Fit",
        subtitle: "Proven Demand and Growth",
        content: `
            <div style="text-align: left; font-size: 14px; line-height: 1.7;">
                <h2 style="color: #00D084; margin-bottom: 8px; font-size: 18px;">Strong Traction & Validation</h2>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-bottom: 8px;">
                    <div style="border: 1px solid #e0e0e0; padding: 15px; border-radius: 6px;">
                        <p style="color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; font-weight: bold;">Community Metrics</p>
                        <p style="margin: 8px 0;">2,500+ GitHub stars (organic growth)</p>
                        <p style="margin: 8px 0;">15,000+ monthly downloads</p>
                        <p style="margin: 8px 0;">8,000+ VS Code extension installs</p>
                        <p style="margin: 8px 0;">3,200+ daily active users</p>
                    </div>

                    <div style="border: 1px solid #e0e0e0; padding: 15px; border-radius: 6px;">
                        <p style="color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 8px; font-weight: bold;">Growth & Performance</p>
                        <p style="margin: 8px 0;">25% month-over-month growth</p>
                        <p style="margin: 8px 0;">92% customer retention rate</p>
                        <p style="margin: 8px 0;">94% test generation accuracy</p>
                        <p style="margin: 8px 0;">NPS Score: 72 (excellent)</p>
                    </div>
                </div>

                <div style="background: #f0f9f6; border-left: 4px solid #00D084; padding: 15px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 8px;">Market Validation</p>
                    <p style="margin: 8px 0;">15+ early adopter companies in production</p>
                    <p style="margin: 8px 0;">40+ hours per developer saved monthly</p>
                    <p style="margin: 8px 0;">35% expansion revenue growth month-over-month</p>
                </div>
            </div>
        `
    },
    {
        title: "Join the QAMill Community",
        subtitle: "Built by Developers, for Developers",
        content: `
            <div style="text-align: center; font-size: 14px; line-height: 1.8;">
                <h2 style="color: #00D084; margin-bottom: 30px; font-size: 18px;">Growing Community of Developers</h2>

                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-bottom: 30px;">
                    <div style="border: 1px solid #e0e0e0; padding: 16px; border-radius: 8px;">
                        <p style="color: #00D084; font-weight: bold; font-size: 18px; margin: 0;">2,500+</p>
                        <p style="color: #666; font-size: 13px; margin-top: 6px;">GitHub Stars</p>
                    </div>
                    <div style="border: 1px solid #e0e0e0; padding: 16px; border-radius: 8px;">
                        <p style="color: #00D084; font-weight: bold; font-size: 18px; margin: 0;">8,000+</p>
                        <p style="color: #666; font-size: 13px; margin-top: 6px;">VS Code Installs</p>
                    </div>
                    <div style="border: 1px solid #e0e0e0; padding: 16px; border-radius: 8px;">
                        <p style="color: #00D084; font-weight: bold; font-size: 18px; margin: 0;">3,200+</p>
                        <p style="color: #666; font-size: 13px; margin-top: 6px;">Daily Active Users</p>
                    </div>
                </div>

                <div style="background: #f0f9f6; border-left: 4px solid #00D084; padding: 20px; margin-bottom: 6px; text-align: left;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 8px; font-size: 15px;">Start Using QAMill Today</p>
                    <p style="margin: 0; color: #666; font-size: 13px;">Right-click any file in VS Code. Select "Generate Tests with QAMill." Watch tests appear in real-time. No setup required.</p>
                </div>

                <div style="margin-bottom: 8px;">
                    <p style="color: #666; font-size: 13px; margin-bottom: 8px; font-weight: bold;">Available On:</p>
                    <p style="margin: 8px 0; font-size: 13px;">
                        <strong>VS Code Marketplace</strong> - Full extension with all features
                    </p>
                    <p style="margin: 8px 0; font-size: 13px;">
                        <strong>GitHub</strong> - Open source, contribute and fork
                    </p>
                    <p style="margin: 8px 0; font-size: 13px;">
                        <strong>NPM</strong> - CLI tool for automation
                    </p>
                </div>

                <div style="background: #f9f9f9; border: 1px solid #e0e0e0; padding: 16px; border-radius: 8px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 8px;">What Developers Say</p>
                    <p style="margin: 0; color: #666; font-size: 13px;">NPS 72 | 92% Retention | 94% Accuracy</p>
                </div>

                <p style="margin-top: 5px; color: #00D084; font-weight: bold; font-size: 14px;">Ready to transform your testing workflow?</p>
            </div>
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
                    <div style="text-align: center; margin-bottom: 6px;">
                        <h1 style="color: #1A1A1A; font-size: 32px; margin: 0 0 8px 0;">${slide.title}</h1>
                        <p style="color: #00D084; font-size: 12px; font-weight: 600; margin: 0 0 12px 0;">${slide.subtitle}</p>
                        <hr style="border: none; border-top: 2px solid #00D084; margin: 0 auto 15px auto; width: 80px;">
                    </div>
                    <div style="color: #333;">
                        ${slide.content}
                    </div>
                </div>
                <div class="fullscreen-controls">
                    <button class="fullscreen-nav-btn" onclick="changeFullscreenSlide(-1)">❮ Previous</button>
                    <div style="text-align: center;">
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