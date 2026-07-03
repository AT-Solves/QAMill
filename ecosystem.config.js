// PM2 Ecosystem Configuration
// Production process management, auto-restart, and monitoring

module.exports = {
  apps: [
    {
      name: 'qamill-backend',
      script: './backend/main.py',
      interpreter: 'python3',
      instances: 1,
      exec_mode: 'fork',

      // Environment variables
      env: {
        QAMILL_HOST: '0.0.0.0',
        QAMILL_PORT: '8765',
        ENVIRONMENT: 'production',
        DEBUG: 'false',
      },

      // Restart policy
      restart_delay: 10000, // 10 seconds
      autorestart: true,
      max_restarts: 5,
      min_uptime: '10s',

      // Error handling
      error_file: './logs/error.log',
      out_file: './logs/out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Resource limits
      max_memory_restart: '500M',
      node_args: [],

      // Graceful shutdown
      kill_timeout: 30000,
      wait_ready: true,
      listen_timeout: 10000,

      // Monitoring
      watch: ['backend/'], // Watch for file changes
      ignore_watch: ['logs/', 'node_modules/', '__pycache__/', '.git'],
      max_restarts: 10,

      // Health check
      cron_restart: '0 0 * * *', // Restart daily at midnight
    },
  ],

  // Cluster configuration
  deploy: {
    production: {
      user: 'qamill',
      host: 'your-server.com',
      ref: 'origin/main',
      repo: 'https://github.com/AT-Solves/QAMill.git',
      path: '/opt/qamill',
      'post-deploy': 'pip install -r backend/requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-deploy-local': 'echo "Deploying to production"',
    },
  },
};
