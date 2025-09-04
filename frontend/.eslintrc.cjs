module.exports = {
  env: { browser: true, es2021: true },
  extends: [ 'eslint:recommended', 'plugin:react/recommended' ],
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  settings: { react: { version: '18.0' } },
  plugins: [ 'react' ],
  rules: { 'react/prop-types': 'off' }
};
