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
            <div style="text-align: left; font-size: 15px; line-height: 1.8;">
                <h2 style="color: #00D084; margin-bottom: 20px; font-size: 24px;">QAMill</h2>
                <p style="margin-bottom: 20px;"><strong>Enterprise-Grade AI Mutation Testing Platform</strong></p>

                <p style="margin-bottom: 15px;"><strong>Problem:</strong> Development teams waste 40% of time writing tests manually, resulting in weak test suites and expensive production bugs averaging $2.4M each.</p>

                <p style="margin-bottom: 15px;"><strong>Solution:</strong> AI-powered test generation combined with mutation testing. Generate comprehensive test suites in 30-60 seconds. Verify tests actually catch bugs.</p>

                <p style="margin-bottom: 15px;"><strong>Market:</strong> $15 billion testing automation market growing 12% annually. $3.5B AI-powered test generation segment. $150M realistic 5-year capture.</p>

                <p style="margin-bottom: 15px;"><strong>Differentiation:</strong> Only platform with true multi-language support (Python, JavaScript, TypeScript, React) + mutation testing + 6+ LLM providers. 10x faster than competitors. Right-click IDE integration with real-time streaming results.</p>

                <p style="margin-bottom: 20px;"><strong>Traction:</strong> 2,500+ GitHub stars, 8,000+ VS Code extension installs, 3,200+ daily active users, 92% customer retention, 25% month-over-month growth.</p>

                <div style="background: #f9f9f9; border-left: 3px solid #00D084; padding: 15px; margin-top: 20px;">
                    <p style="color: #00D084; font-weight: bold; margin-bottom: 12px;">12-Month Roadmap</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Now (Q3 2026):</strong> v1.2.2 production-ready, multi-language, 6+ LLM providers, mutation testing</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Q4 2026:</strong> Pro SaaS tier launch ($10-50/mo), cloud hosting, 5K users target</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Q1 2027:</strong> Enterprise on-premises, SSO integration, 25 customers target</p>
                    <p style="margin: 8px 0; font-size: 14px;"><strong>Q2-Q4 2027:</strong> 4 new languages (Go, Rust, Java, C#), AI-powered test refactoring, Series B funding</p>
                </div>

                <p style="margin-top: 20px;"><strong>Business Model:</strong> 3-tier revenue: Free open-source (millions of users), Pro SaaS ($1.2-6M Y1 ARR), Enterprise ($1.2-12M Y3 ARR). Projected $20M+ ARR by Year 5.</p>

                <p style="margin-top: 15px; color: #00D084; font-weight: bold;">Ask: Series A funding to scale sales, expand language support, and capture market leadership.</p>
            </div>
        `
    },
    {
        title: "Market Problem",
        subtitle: "The Opportunity",
        content: `
            <div style="text-align: left; font-size: 15px; line-height: 1.8;">
                <h2 style="color: #00D084; margin-bottom: 25px; font-size: 24px;">Testing Remains the Bottleneck</h2>

                <div style="margin-bottom: 20px;">
                    <p style="margin: 12px 0;"><strong>87% of teams</strong> spend 40% of development time writing tests manually</p>
                    <p style="margin: 12px 0;"><strong>72% report</strong> inadequate test coverage and missed edge cases</p>
                    <p style="margin: 12px 0;"><strong>91% struggle</strong> with test maintenance when code changes</p>
                    <p style="margin: 12px 0;"><strong>64% maintain</strong> 3+ languages with separate testing workflows</p>
                    <p style="margin: 12px 0;"><strong>Average cost:</strong> $2.4M per production bug that escapes testing</p>
                </div>

                <div style="background: #f9f9f9; border-left: 3px solid #00D084; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Impact:</strong> Teams lose 2+ days of productivity per developer per week. Code quality lags. Bugs reach production. Development velocity stalls.</p>
                </div>

                <p style="margin-top: 20px; color: #666; font-size: 13px;">Data sources: StackOverflow Developer Survey 2024, GitHub State of Octoverse 2024, Gartner Report 2024, Forrester Research 2024, JetBrains Ecosystem Survey 2024</p>
            </div>
        `
    },
    {
        title: "Market Size & Opportunity",
        subtitle: "$15 Billion Testing Automation Market",
        content: `
            <div style="text-align: center; font-size: 15px;">
                <h2 style="color: #00D084; margin-bottom: 30px; font-size: 24px;">Massive Addressable Market</h2>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-bottom: 30px;">
                    <div style="text-align: left; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
                        <p style="color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 10px;">TAM - Total Addressable Market</p>
                        <p style="color: #00D084; font-size: 32px; font-weight: bold; margin: 0;">$15B</p>
                        <p style="color: #666; font-size: 13px; margin-top: 8px;">Global testing automation market growing 12% annually</p>
                    </div>
                    <div style="text-align: left; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px;">
                        <p style="color: #666; font-size: 12px; text-transform: uppercase; margin-bottom: 10px;">SAM - Serviceable Addressable Market</p>
                        <p style="color: #00D084; font-size: 32px; font-weight: bold; margin: 0;">$3.5B</p>
                        <p style="color: #666; font-size: 13px; margin-top: 8px;">AI-powered test generation segment (our focus)</p>
                    </div>
                </div>

                <div style="background: #f0f9f6; border-left: 4px solid #00D084; padding: 20px; margin: 20px 0; text-align: left;">
                    <p style="color: #00D084; font-weight: bold; font-size: 16px; margin-bottom: 10px;">SOM - Serviceable Obtainable Market (Year 5)</p>
                    <p style="margin: 0; font-size: 16px;"><strong style="color: #00D084;">$150M</strong> - Conservative, realistic capture target</p>
                </div>

                <div style="text-align: left; margin-top: 20px; font-size: 14px;">
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
                <h2 style="color: #00D084; margin-bottom: 20px; font-size: 24px;">How QAMill Works</h2>

                <div style="margin-bottom: 25px;">
                    <p style="margin: 12px 0;"><strong>Ultra-Fast Generation:</strong> Generates comprehensive test suites in 30-60 seconds. Real-time streaming shows progress as tests are created.</p>

                    <p style="margin: 12px 0;"><strong>Multi-Language Support:</strong> Native support for Python, JavaScript, TypeScript, and React. Single platform for entire tech stack.</p>

                    <p style="margin: 12px 0;"><strong>Mutation Testing:</strong> Automatically detects weak tests and generates healing tests. Verifies tests actually catch bugs.</p>

                    <p style="margin: 12px 0;"><strong>LLM Flexibility:</strong> Choose from 6+ AI providers (Claude, GPT-4, Ollama, Grok, Gemini, DeepSeek, Mistral). No vendor lock-in.</p>

                    <p style="margin: 12px 0;"><strong>IDE Integration:</strong> VS Code extension with right-click action. Generate tests directly from your editor without context switching.</p>

                    <p style="margin: 12px 0;"><strong>Professional Reports:</strong> Elite HTML reports with mutation analysis, coverage metrics, and actionable insights.</p>
                </div>

                <div style="background: #f0f9f6; border-left: 4px solid #00D084; padding: 15px; margin-top: 20px;">
                    <p style="margin: 0;"><strong>Enterprise Grade:</strong> On-premises deployment, offline capability, 100% backward compatibility, 92% customer retention.</p>
                </div>
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