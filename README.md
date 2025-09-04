# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      ...tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      ...tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      ...tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```


```
mediadownloader_web
├─ .env
├─ eslint.config.js
├─ index.html
├─ package-lock.json
├─ package.json
├─ postcss.config.js
├─ public
│  ├─ icons
│  │  ├─ facebook.svg
│  │  ├─ favicon.svg
│  │  ├─ instagram.svg
│  │  ├─ x.svg
│  │  └─ youtube.svg
│  └─ vite.svg
├─ README.md
├─ server
│  ├─ .env.example
│  ├─ app
│  │  ├─ main.py
│  │  ├─ models
│  │  │  ├─ schemas.py
│  │  │  └─ __pycache__
│  │  │     └─ schemas.cpython-313.pyc
│  │  ├─ routers
│  │  │  ├─ media.py
│  │  │  └─ __pycache__
│  │  │     └─ media.cpython-313.pyc
│  │  ├─ services
│  │  │  ├─ job_manager.py
│  │  │  ├─ ytdlp_service.py
│  │  │  └─ __pycache__
│  │  │     ├─ job_manager.cpython-313.pyc
│  │  │     └─ ytdlp_service.cpython-313.pyc
│  │  └─ __pycache__
│  │     └─ main.cpython-313.pyc
│  ├─ cookies
│  │  └─ facebook.txt
│  ├─ requirements.txt
│  └─ run_dev.sh
├─ setup.ps1
├─ src
│  ├─ app
│  │  ├─ router.tsx
│  │  └─ store.ts
│  ├─ App.css
│  ├─ App.tsx
│  ├─ assets
│  │  └─ react.svg
│  ├─ components
│  │  ├─ DownloadItem.tsx
│  │  ├─ DownloadOptionsModal.tsx
│  │  ├─ FloatingBubble.tsx
│  │  └─ Header.tsx
│  ├─ features
│  │  └─ downloads
│  │     ├─ downloads.slice.ts
│  │     └─ types.ts
│  ├─ hooks
│  │  ├─ useClipboardUrl.ts
│  │  └─ useModal.ts
│  ├─ index.css
│  ├─ lib
│  │  ├─ api.ts
│  │  ├─ config.ts
│  │  ├─ mediaApi.ts
│  │  └─ validators.ts
│  ├─ main.tsx
│  ├─ pages
│  │  ├─ Downloads.tsx
│  │  ├─ Home.tsx
│  │  └─ Settings.tsx
│  ├─ styles
│  │  └─ tailwind.css
│  ├─ utils
│  │  ├─ format.ts
│  │  └─ platform.ts
│  └─ vite-env.d.ts
├─ tailwind.config.ts
├─ tsconfig.app.json
├─ tsconfig.json
├─ tsconfig.node.json
└─ vite.config.ts

```