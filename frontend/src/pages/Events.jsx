import { useState, useEffect } from 'react';
import axios from 'axios';
import EventCard from '../components/EventCard';
import VideoModal from '../components/VideoModal';

const Events = () => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedEvent, setSelectedEvent] = useState(null);

    useEffect(() => {
        fetchEvents();
    }, []);

    const fetchEvents = async () => {
        try {
            // Assuming backend is playing on 8000
            const res = await axios.get('http://localhost:8000/api/events');
            setEvents(res.data);
        } catch (error) {
            console.error("Failed to fetch events", error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div>
            <h1 className="text-2xl font-bold mb-6">Security Events</h1>

            {loading ? (
                <div className="text-secondary">Loading events...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {events.map((event, idx) => (
                        <EventCard
                            key={event.clip_id || idx}
                            event={event}
                            onClick={setSelectedEvent}
                        />
                    ))}
                </div>
            )}

            {selectedEvent && (
                <VideoModal
                    event={selectedEvent}
                    onClose={() => setSelectedEvent(null)}
                />
            )}
        </div>
    );
};

export default Events;
