// QAMill VS Code Extension Configuration
// Centralized configuration for hardcoded values

import * as vscode from 'vscode';

export const CONFIG = {
  // Extension metadata
  EXTENSION: {
    ID: 'achieverthoughts.qamill-mutation-testing',
    NAME: 'QAMill',
    PUBLISHER: 'achieverthoughts',
  },

  // Server configuration
  SERVER: {
    HOST: 'localhost',
    PORT: 8765,
    get URL() {
      return `http://${this.HOST}:${this.PORT}`;
    },
  },

  // API endpoints
  API: {
    ANALYZE: '/analyze',
    ANALYZE_JAVASCRIPT: '/analyze/javascript',
    STREAM: '/stream',
    GENERATE_UNIT_TESTS: '/generate/unit-tests/stream',
    GENERATE_MANUAL_TESTS: '/generate/manual-tests/stream',
    HEALTH: '/health',
  },

  // Timeout configuration (milliseconds)
  TIMEOUT: {
    DEFAULT: 30000,
    LONG: 60000,
    SHORT: 5000,
  },

  // UI Configuration
  UI: {
    PROGRESS_UPDATE_INTERVAL: 100,
    MAX_OUTPUT_LINES: 1000,
  },

  // Features
  FEATURES: {
    MUTATION_TESTING: true,
    TEST_GENERATION: true,
    EQUIVALENCE_DETECTION: true,
    AUTO_HEALING: true,
    FAST_MODE: false,
  },

  // Supported languages
  LANGUAGES: {
    PYTHON: { ext: 'py', scheme: 'file' },
    JAVASCRIPT: { ext: 'js', scheme: 'file' },
    TYPESCRIPT: { ext: 'ts', scheme: 'file' },
    JAVASCRIPT_REACT: { ext: 'jsx', scheme: 'file' },
    TYPESCRIPT_REACT: { ext: 'tsx', scheme: 'file' },
  },

  // LLM Providers
  LLM_PROVIDERS: [
    'claude',
    'gpt',
    'ollama',
    'grok',
    'gemini',
    'deepseek',
    'mistral',
    'inhouse',
  ],

  // Commands
  COMMANDS: {
    ANALYZE: 'amil.analyze',
    GENERATE_TESTS: 'amil.generateTests',
    GENERATE_MANUAL_TESTS: 'amil.generateManualTests',
    CHECK_QUALITY: 'amil.checkQuality',
    SHOW_DASHBOARD: 'amil.showDashboard',
  },

  // Context keys
  CONTEXT: {
    ANALYSIS_RUNNING: 'amil.analysisRunning',
    EXTENSION_READY: 'amil.extensionReady',
  },

  // Settings keys
  SETTINGS: {
    LLM_PROVIDER: 'amil.llmProvider',
    BACKEND_PORT: 'amil.backendPort',
    FAST_MODE: 'amil.fastMode',
    API_KEYS: {
      ANTHROPIC: 'amil.anthropicApiKey',
      OPENAI: 'amil.openaiApiKey',
      GROK: 'amil.grokApiKey',
    },
    OLLAMA_MODEL: 'amil.ollamaModel',
  },

  // Get configuration value
  getSetting<T>(key: string, defaultValue?: T): T | undefined {
    const config = vscode.workspace.getConfiguration();
    return config.get(key, defaultValue);
  },

  // Update configuration value
  async updateSetting(key: string, value: any): Promise<void> {
    const config = vscode.workspace.getConfiguration();
    await config.update(key, value, vscode.ConfigurationTarget.Global);
  },
};

// Export helper functions
export function getBackendUrl(): string {
  const port = CONFIG.getSetting<number>(CONFIG.SETTINGS.BACKEND_PORT, CONFIG.SERVER.PORT);
  return `http://${CONFIG.SERVER.HOST}:${port}`;
}

export function getLLMProvider(): string {
  return CONFIG.getSetting<string>(CONFIG.SETTINGS.LLM_PROVIDER, 'claude') || 'claude';
}

export function isFastMode(): boolean {
  return CONFIG.getSetting<boolean>(CONFIG.SETTINGS.FAST_MODE, false) || false;
}

export function getLanguageFileTypes(): string[] {
  return Object.values(CONFIG.LANGUAGES).map(lang => `*.${lang.ext}`);
}
