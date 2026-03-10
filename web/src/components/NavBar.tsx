import { Link, useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/runs', label: 'Runs' },
  { to: '/taxonomy', label: 'Taxonomy' },
]

export function NavBar() {
  const location = useLocation()

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 border-b border-zinc-800 bg-zinc-950/95 backdrop-blur supports-[backdrop-filter]:bg-zinc-950/75">
      <div className="flex h-full items-center px-6 gap-8">
        <Link to="/" className="font-semibold text-lg tracking-tight text-white">
          Crodino
        </Link>
        <div className="flex items-center gap-1">
          {links.map(({ to, label }) => {
            const active = to === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(to)
            return (
              <Link
                key={to}
                to={to}
                className={cn(
                  'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                  active
                    ? 'bg-zinc-800 text-white'
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
                )}
              >
                {label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
