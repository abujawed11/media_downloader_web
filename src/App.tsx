
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

export default function App() {
  return (
    <div className="min-h-dvh text-white">
      <Header />
      <main className="container py-8">
        <Outlet />
      </main>

      {/* Modals live at root */}
      <DownloadOptionsModal />
    </div>
  )
}

