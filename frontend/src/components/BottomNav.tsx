import { NavLink } from 'react-router-dom';

const items = [
  { to: '/home', label: 'Home', icon: '⌂' },
  { to: '/services', label: 'Services', icon: '▦' },
  { to: '/ai', label: 'AI', icon: '✦', ai: true },
  { to: '/transactions', label: 'History', icon: '☰' },
  { to: '/more', label: 'More', icon: '⋯' },
];

export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Main">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `nav-item${isActive ? ' active' : ''}${item.ai ? ' ai-nav' : ''}`
          }
        >
          <span className="nav-icon" aria-hidden>
            {item.icon}
          </span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
