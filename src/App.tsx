
// import './App.css'

// function App() {


//   return (
//     <>
//       <div>Hello World</div>
//     </>
//   )
// }

// export default App

import { Outlet } from 'react-router-dom'
import Header from './components/Header'
import DownloadOptionsModal from './components/DownloadOptionsModal'
import MiniPlayer from './components/MiniPlayer'
import { PlayerProvider } from './context/PlayerContext'

export default function App() {
  return (
    <PlayerProvider>
      <div className="min-h-dvh text-white">
        <Header />
        <main className="container mx-auto px-6 py-8">
          <Outlet />
        </main>

        {/* Modals live at root */}
        <DownloadOptionsModal />

        {/* Floating mini player — visible when user minimizes a video */}
        <MiniPlayer />
      </div>
    </PlayerProvider>
  )
}

