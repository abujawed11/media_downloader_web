import { NavLink } from 'react-router-dom'

const linkBase = 'btn-ghost'
const active = 'bg-white/10'

export default function Header() {
  return (
    <header className="border-b border-white/10">
      <div className="container flex items-center justify-between py-4">
        <div className="flex items-center gap-3">
          <div className="size-9 rounded-full bg-yellow-400" />
          <h1 className="text-xl font-semibold">MediaDownloader Web</h1>
        </div>
        <nav className="flex gap-2">
          <NavLink to="/" end className={({isActive}) => `${linkBase} ${isActive ? active : ''}`}>Home</NavLink>
          <NavLink to="/downloads" className={({isActive}) => `${linkBase} ${isActive ? active : ''}`}>Downloads</NavLink>
          <NavLink to="/settings" className={({isActive}) => `${linkBase} ${isActive ? active : ''}`}>Settings</NavLink>
        </nav>
      </div>
    </header>
  )
}
