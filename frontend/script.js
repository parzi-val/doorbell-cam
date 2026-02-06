document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('event-grid');
    const modal = document.getElementById('video-modal');
    const closeBtn = document.querySelector('.close-btn');
    const videoPlayer = document.getElementById('main-video');

    // Modal Elements
    const mTitle = document.getElementById('modal-title');
    const mTime = document.getElementById('modal-timestamp');
    const mTags = document.getElementById('modal-tags');
    const mSummary = document.getElementById('modal-summary');
    const mStats = document.getElementById('modal-stats');

    // Fetch Events
    fetch('/api/events')
        .then(res => res.json())
        .then(events => {
            document.getElementById('status').textContent = `${events.length} Events Found`;
            renderGrid(events);
        })
        .catch(err => {
            console.error(err);
            document.getElementById('status').textContent = 'Error loading events';
        });

    function renderGrid(events) {
        grid.innerHTML = '';
        events.forEach(event => {
            const card = document.createElement('div');
            card.className = 'card';

            const date = new Date(event.timestamp * 1000);
            const timeStr = date.toLocaleString();

            const hasWeapon = event.weapon_detected;
            const level = event.final_level || event.trigger_level;

            let tagsHtml = `<span class="tag tag-${level === 'THREAT' ? 'threat' : 'sus'}">${level}</span>`;
            if (hasWeapon) tagsHtml += `<span class="tag tag-weapon">WEAPON</span>`;

            card.innerHTML = `
                <div class="card-thumb">
                    <span>Play Video</span>
                </div>
                <div class="card-content">
                    <div class="card-title">
                        <span>${level}</span>
                        ${hasWeapon ? '🔫' : ''}
                    </div>
                    <div class="card-meta">
                        <div>${timeStr}</div>
                        <div>Intent: ${event.max_intent.toFixed(2)}</div>
                    </div>
                    <div style="margin-top:0.5rem;">${tagsHtml}</div>
                </div>
            `;

            card.onclick = () => openModal(event);
            grid.appendChild(card);
        });
    }

    function openModal(event) {
        modal.classList.remove('hidden');
        videoPlayer.src = event.video_url;
        videoPlayer.play();

        mTitle.textContent = event.final_level;
        mTime.textContent = new Date(event.timestamp * 1000).toLocaleString();

        // Tags
        let tagsHtml = `<span class="tag tag-${event.final_level === 'THREAT' ? 'threat' : 'sus'}">${event.final_level}</span>`;
        if (event.weapon_detected) tagsHtml += `<span class="tag tag-weapon">WEAPON</span>`;
        mTags.innerHTML = tagsHtml;

        // Summary
        mSummary.textContent = event.summary || "No summary available.";

        // Stats
        let statsHtml = `
            <div class="stat-item">
                <span class="stat-label">Max Intent</span>
                <span class="stat-value">${event.max_intent.toFixed(2)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Mean Intent</span>
                <span class="stat-value">${event.mean_intent ? event.mean_intent.toFixed(2) : 'N/A'}</span>
            </div>
        `;

        if (event.signals_stats && event.signals_stats.weapon_score) {
            statsHtml += `
            <div class="stat-item">
                <span class="stat-label">Weapon Conf</span>
                <span class="stat-value">${(event.signals_stats.weapon_score.max * 100).toFixed(0)}%</span>
            </div>`;
        }

        mStats.innerHTML = statsHtml;
    }

    closeBtn.onclick = () => {
        modal.classList.add('hidden');
        videoPlayer.pause();
        videoPlayer.src = "";
    };

    window.onclick = (e) => {
        if (e.target === modal) {
            closeBtn.click();
        }
    };
});
