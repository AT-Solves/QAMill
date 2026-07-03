// QAMill Website Configuration
// Centralized constants for all hardcoded values

export const CONFIG = {
  // UI Configuration
  UI: {
    ZOOM: {
      INITIAL: 100,
      MIN: 50,
      MAX: 200,
      INCREMENT: 10,
    },
    SLIDE: {
      BASE_HEIGHT: 600,
    },
    TOUCH: {
      SWIPE_THRESHOLD: 50,
    },
    SCROLL: {
      NAVBAR_SHADOW_THRESHOLD: 50,
    },
    OBSERVER: {
      THRESHOLD: 0.1,
      ROOT_MARGIN: '0px 0px -50px 0px',
    },
    TIMING: {
      SCROLL_SMOOTH_BEHAVIOR: 'smooth',
    },
  },

  // External Links
  LINKS: {
    MARKETPLACE: 'https://marketplace.visualstudio.com/items?itemName=achieverthoughts.qamill-mutation-testing',
    GITHUB: 'https://github.com/AT-Solves/QAMill',
    GITHUB_ISSUES: 'https://github.com/AT-Solves/QAMill/issues',
    DOCS: 'https://github.com/AT-Solves/QAMill/wiki',
  },

  // LLM Providers
  PROVIDERS: [
    'Claude',
    'GPT',
    'Ollama',
    'Grok',
    'Gemini',
    'DeepSeek',
    'Mistral',
  ],

  // Colors (for reference, CSS variables should be used in CSS)
  COLORS: {
    PRIMARY: '#00D084',
    SECONDARY: '#0d4a4a',
    TEXT_PRIMARY: '#333',
    TEXT_SECONDARY: '#666',
    BACKGROUND_LIGHT: '#f9f9f9',
    BACKGROUND_WHITE: '#FFFFFF',
  },

  // Spacing values (for reference, CSS variables should be used in CSS)
  SPACING: {
    SM: '8px',
    MD: '15px',
    LG: '20px',
    XL: '25px',
  },

  // Border radius (for reference, CSS variables should be used in CSS)
  BORDER_RADIUS: '8px',

  // SVG Configuration
  SVG: {
    ICON_SIZE: 50,
    ICON_VIEWBOX: '0 0 50 50',
    ICON_STROKE_WIDTH: 2,
    ICON_COLOR: '#00D084',
  },
};

// Export as default for easy access
export default CONFIG;
