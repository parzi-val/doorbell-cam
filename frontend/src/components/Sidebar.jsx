import { Home, Camera, AlertTriangle, Menu, TestTube } from 'lucide-react';
import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';

const Sidebar = () => {
    const [collapsed, setCollapsed] = useState(false);

    const navItems = [
        { icon: Home, label: 'Dashboard', path: '/' },
        { icon: AlertTriangle, label: 'Events', path: '/events' },
        { icon: Camera, label: 'Live Monitor', path: '/live' },
        { icon: TestTube, label: 'Simulation', path: '/test' },
    ];

    return (
        <div
            className={clsx(
                "h-screen bg-card border-r border-border transition-all duration-300 flex flex-col",
                collapsed ? "w-16" : "w-64"
            )}
        >
            <div className="p-4 flex items-center justify-between border-b border-border">
                {!collapsed && <span className="font-bold text-lg text-primary">Security</span>}
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="p-2 hover:bg-slate-100 rounded-md text-secondary hover:text-primary transition-colors"
                >
                    <Menu size={20} />
                </button>
            </div>

            <nav className="flex-1 p-2 gap-2 flex flex-col">
                {navItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) => clsx(
                            "flex items-center gap-3 p-3 rounded-md transition-colors",
                            isActive
                                ? "bg-accent-red/10 text-accent-red"
                                : "text-secondary hover:bg-slate-100 hover:text-primary",
                            collapsed && "justify-center"
                        )}
                    >
                        <item.icon size={20} />
                        {!collapsed && <span>{item.label}</span>}
                    </NavLink>
                ))}
            </nav>
        </div>
    );
};

export default Sidebar;
