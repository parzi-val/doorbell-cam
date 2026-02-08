import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import Live from './pages/Live';
import Events from './pages/Events';
import Test from './pages/Test';

// Placeholders
const Home = () => <div className="text-2xl font-bold">Dashboard Home (Coming Soon)</div>;

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<MainLayout />}>
                    <Route index element={<Home />} />
                    <Route path="events" element={<Events />} />
                    <Route path="live" element={<Live />} />
                    <Route path="test" element={<Test />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
            </Routes>
        </BrowserRouter>
    );
}

export default App;
