import { NavLink } from 'react-router-dom'
import { Film } from 'lucide-react'

const linkBase = 'btn-ghost'
const active = 'bg-white/10'

export default function Header() {
  return (
    <header className="border-b border-white/10 sticky top-0 z-50 backdrop-blur-sm bg-black/60">
      <div className="container flex items-center justify-between py-3">
        <div className="flex items-center gap-3">
          <div className="size-8 rounded-full bg-yellow-400 flex items-center justify-center">
            <Film className="size-4 text-black" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">MediaLib</h1>
        </div>
        <nav className="flex gap-1">
          <NavLink to="/" end className={({ isActive }) => `${linkBase} ${isActive ? active : ''}`}>
            Upload
          </NavLink>
          <NavLink to="/library" className={({ isActive }) => `${linkBase} ${isActive ? active : ''}`}>
            Library
          </NavLink>
          <NavLink to="/uploads" className={({ isActive }) => `${linkBase} ${isActive ? active : ''}`}>
            Uploads
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => `${linkBase} ${isActive ? active : ''}`}>
            Settings
          </NavLink>
        </nav>
      </div>
    </header>
  )
}
