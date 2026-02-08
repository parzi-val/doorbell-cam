import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';

const MainLayout = () => {
    return (
        <div className="flex bg-background min-h-screen text-primary">
            <Sidebar />
            <main className="flex-1 overflow-auto">
                <div className="p-8">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

export default MainLayout;
