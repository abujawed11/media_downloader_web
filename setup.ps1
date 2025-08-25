# Frontend folders
mkdir src\app, src\pages, src\components, src\features\downloads, src\lib, src\hooks, src\utils, src\styles, public\icons | Out-Null

# Frontend files (empty placeholders)
ni src\app\router.tsx -ItemType File
ni src\app\store.ts -ItemType File
ni src\pages\Home.tsx -ItemType File
ni src\pages\Downloads.tsx -ItemType File
ni src\pages\Settings.tsx -ItemType File
ni src\components\FloatingBubble.tsx -ItemType File
ni src\components\DownloadOptionsModal.tsx -ItemType File
ni src\components\DownloadItem.tsx -ItemType File
ni src\components\Header.tsx -ItemType File
ni src\features\downloads\downloads.slice.ts -ItemType File
ni src\features\downloads\types.ts -ItemType File
ni src\lib\api.ts -ItemType File
ni src\lib\mediaApi.ts -ItemType File
ni src\lib\config.ts -ItemType File
ni src\lib\validators.ts -ItemType File
ni src\hooks\useClipboardUrl.ts -ItemType File
ni src\hooks\useModal.ts -ItemType File
ni src\utils\platform.ts -ItemType File
ni src\utils\format.ts -ItemType File
ni src\styles\tailwind.css -ItemType File
ni public\icons\favicon.svg -ItemType File
ni public\icons\youtube.svg -ItemType File
ni public\icons\instagram.svg -ItemType File
ni public\icons\facebook.svg -ItemType File
ni public\icons\x.svg -ItemType File

# Tailwind & PostCSS config placeholders
ni tailwind.config.ts -ItemType File
ni postcss.config.js -ItemType File

# Backend structure (optional but recommended)
mkdir server, server\app, server\app\routers, server\app\services, server\app\models | Out-Null
ni server\app\main.py -ItemType File
ni server\app\routers\media.py -ItemType File
ni server\app\services\ytdlp_service.py -ItemType File
ni server\app\models\schemas.py -ItemType File
ni server\requirements.txt -ItemType File
ni server\.env.example -ItemType File
ni server\run_dev.sh -ItemType File
